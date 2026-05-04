from langchain_openai import ChatOpenAI

from app.config import settings


def build_chat_openai(*, temperature: float | None = None) -> ChatOpenAI:
    kwargs: dict[str, str | float | None] = {
        "model": settings.llm_model,
        "api_key": settings.openai_api_key,
    }
    if temperature is not None and not settings.llm_model.startswith("gpt-5"):
        kwargs["temperature"] = temperature
    return ChatOpenAI(**kwargs)
