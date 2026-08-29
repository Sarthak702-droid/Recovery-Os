from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite+aiosqlite:///./recoveros.db"
    redis_url: str = "redis://localhost:6379/0"
    merchant_id: str = ""
    merchant_name: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = "dev_webhook_secret"
    ai_backend: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:1.7b"
    ollama_embedding_model: str = "bge-small-en-v1.5"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    app_env: str = "development"
    policy_version: str = "merchant-policy-v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
