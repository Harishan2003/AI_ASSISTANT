from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.llm.models import LLMProvider


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==================================================
    # APP
    # ==================================================

    app_name: str = "AI Assistant"
    app_version: str = "2.0.0"
    debug: bool = True

    # ==================================================
    # LLM PROVIDER
    # ==================================================

    llm_provider: LLMProvider = LLMProvider.GROQ

    temperature: float = 0.7
    max_tokens: int = 1024
    timeout: int = 60

    # ==================================================
    # GROQ
    # ==================================================

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_url: str = "https://api.groq.com/openai/v1"

    # ==================================================
    # TAVILY WEB SEARCH
    # ==================================================

    tavily_api_key: str = ""
    tavily_search_depth: str = "fast"
    tavily_max_results: int = 5
    

    # ==================================================
    # OLLAMA
    # ==================================================

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"

    # ==================================================
    # OPENROUTER
    # ==================================================

    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-chat"
    openrouter_url: str = "https://openrouter.ai/api/v1"

    # ==================================================
    # OPENAI
    # ==================================================

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_url: str = "https://api.openai.com/v1"

    # ==================================================
    # DATABASE
    # ==================================================

    database_url: str = "sqlite:///./assistant.db"

    # ==================================================
    # JWT
    # ==================================================

    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
