from __future__ import annotations

from sqlalchemy.orm import Session

from app.bot.entity_extractor import LeadExtractedData, extract_entities
from app.database.models import MessageSender
from app.database.repositories import ConversationRepository
from app.database.session import SessionLocal
from app.services.lead_service import LeadService

SHORT_TERM_MEMORY_LIMIT = 10


def get_conversation_context(conversation_id: int, db: Session | None = None) -> list[dict[str, str]]:
    """Return last 10 messages as role/content pairs for a conversation."""
    owns_session = db is None
    if db is None:
        db = SessionLocal()

    conversation_repo = ConversationRepository(db)
    messages = conversation_repo.get_conversation_messages(conversation_id)
    short_history = messages[-SHORT_TERM_MEMORY_LIMIT:]

    context: list[dict[str, str]] = []
    for message in short_history:
        role = "assistant" if message.sender == MessageSender.BOT else "user"
        context.append({"role": role, "content": message.text})

    if owns_session:
        db.close()

    return context


def update_lead_from_message(
    conversation_id: int,
    phone: str,
    message_text: str,
    db: Session,
    extracted: LeadExtractedData | None = None,
) -> None:
    """Upsert lead and persist extracted fields on each incoming message."""
    lead_service = LeadService(db)
    lead = lead_service.get_or_create_lead(conversation_id=conversation_id, phone=phone)

    data = extracted or extract_entities(message_text)
    lead_service.update_lead_from_extracted(lead=lead, extracted=data)
