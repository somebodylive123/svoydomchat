from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = Field(default="SVOYDOM AI WhatsApp Bot")
    app_env: str = Field(default="dev")
    debug: bool = Field(default=True)

    api_prefix: str = Field(default="/api")

    database_url: str = Field(default="sqlite:///./svoydom.db")
    bitrix_mode: str = Field(default="real", alias="BITRIX_MODE")
    bitrix_webhook_url: str | None = Field(default=None, alias="BITRIX_WEBHOOK_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-5-mini", alias="LLM_MODEL")
    whatsapp_provider: str = Field(default="mock", alias="WHATSAPP_PROVIDER")
    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str | None = Field(default=None, alias="TWILIO_WHATSAPP_FROM")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
