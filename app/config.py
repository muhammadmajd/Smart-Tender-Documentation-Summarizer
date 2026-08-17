from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "anthropic"  # anthropic | openai | ollama

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-8"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    ollama_base_url: str = "http://localhost:11434"  # или https://ollama.com для облака
    ollama_model: str = "llama3.1"
    ollama_api_key: str | None = None  # нужен только для облачного Ollama

    max_text_chars: int = 60000


settings = Settings()
