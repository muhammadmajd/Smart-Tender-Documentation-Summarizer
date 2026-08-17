import json
import logging

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.schemas import TenderSummary

logger = logging.getLogger("tender-summarizer")

SYSTEM_PROMPT = (
    "Ты — ассистент, который анализирует документацию по государственным закупкам "
    "(тендерам) на русском языке. Внимательно изучи текст документа и извлеки только "
    "ту информацию, которая явно в нём присутствует. Ничего не придумывай. Если "
    "какое-то поле не найдено в документе, оставь его пустым (для списков — пустой "
    "список, для текстовых полей — null)."
)

USER_PROMPT_TEMPLATE = (
    "Проанализируй текст тендерной документации ниже и извлеки:\n"
    "1. Сумму контракта (с валютой);\n"
    "2. Сроки выполнения работ/услуг;\n"
    "3. Ключевые требования к исполнителю (списком);\n"
    "4. Штрафы и неустойки за нарушение условий контракта (за что штраф и его "
    "размер, если он указан);\n"
    "5. Краткую выжимку документа (2-4 предложения).\n\n"
    "Текст документа:\n"
    "-----\n"
    "{text}\n"
    "-----"
)

# нужен только OpenAI/Ollama — Anthropic получает схему через output_format
JSON_SCHEMA_HINT = (
    "Ответь СТРОГО в формате JSON без каких-либо пояснений вне JSON, со следующими "
    "полями:\n"
    "{\n"
    '  "contract_amount": string | null,\n'
    '  "deadline": string | null,\n'
    '  "key_requirements": string[],\n'
    '  "penalties": [{"description": string, "amount": string | null}],\n'
    '  "summary": string\n'
    "}"
)


async def summarize_tender(text: str) -> TenderSummary:
    text = text[: settings.max_text_chars]
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        return await _summarize_with_anthropic(text)
    if provider == "openai":
        return await _summarize_with_openai(text)
    if provider == "ollama":
        return await _summarize_with_ollama(text)
    raise ValueError(f"Неизвестный LLM_PROVIDER: {settings.llm_provider!r}")


async def _summarize_with_anthropic(text: str) -> TenderSummary:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)}],
        output_format=TenderSummary,
    )
    return response.parsed_output


async def _summarize_with_openai(text: str) -> TenderSummary:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY не задан")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    # json_object гарантирует валидный JSON, но не нашу схему — отсюда JSON_SCHEMA_HINT
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{JSON_SCHEMA_HINT}"},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    return _parse_json_response(content)


async def _summarize_with_ollama(text: str) -> TenderSummary:
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{JSON_SCHEMA_HINT}"},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},  # иначе младшие модели съезжают с JSON в прозу
    }
    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(f"{settings.ollama_base_url}/api/chat", json=payload, headers=headers)
        resp.raise_for_status()

    content = resp.json()["message"]["content"]
    return _parse_json_response(content)


def _parse_json_response(content: str) -> TenderSummary:
    try:
        return TenderSummary.model_validate_json(content)
    except (ValidationError, json.JSONDecodeError) as exc:
        logger.error("Не удалось разобрать ответ модели: %s", content)
        raise RuntimeError(f"Не удалось разобрать ответ модели как JSON по схеме: {exc}") from exc
