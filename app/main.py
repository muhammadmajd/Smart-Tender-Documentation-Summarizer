import logging

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.config import settings
from app.llm import summarize_tender
from app.pdf_utils import extract_text_from_pdf
from app.schemas import TenderSummary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tender-summarizer")

app = FastAPI(
    title="Тендерный суммаризатор",
    description="Загружает PDF тендерной документации и возвращает краткую выжимку с помощью LLM",
    version="1.0.0",
)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "llm_provider": settings.llm_provider}


@app.post("/summarize", response_model=TenderSummary)
async def summarize(file: UploadFile = File(...)) -> TenderSummary:
    if not (file.filename or "").lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Ожидается PDF-файл")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Файл пуст")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (лимит 20 МБ)")

    try:
        text = extract_text_from_pdf(content)
    except Exception as exc:
        logger.exception("Ошибка при извлечении текста из PDF")
        raise HTTPException(status_code=422, detail=f"Не удалось прочитать PDF: {exc}") from exc

    if not text.strip():
        # pypdf не распознаёт сканы без текстового слоя (OCR не делает)
        raise HTTPException(
            status_code=422,
            detail="Не удалось извлечь текст из PDF (возможно, это скан без OCR)",
        )

    try:
        return await summarize_tender(text)
    except Exception as exc:
        logger.exception("Ошибка при обращении к LLM")
        raise HTTPException(status_code=502, detail=f"Ошибка LLM-провайдера: {exc}") from exc
