from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.bot.agent import run_agent
from app.bot.entity_extractor import extract_entities
from app.bot.handover import perform_handover, should_handover_to_manager, should_resume_bot_from_handover
from app.core.logger import logger
from app.database.models import ConversationStatus, MessageSender
from app.database.repositories import ConversationRepository
from app.database.session import SessionLocal
from app.services.crm_service import CRMService
from app.services.lead_service import LeadService


def _format_history_for_agent(
    repository: ConversationRepository,
    conversation_id: int,
    *,
    exclude_last_user_message: bool = False,
) -> list[str]:
    messages = repository.get_conversation_messages(conversation_id)
    formatted: list[str] = []
    for message in messages:
        if message.sender == MessageSender.BOT:
            formatted.append(f"assistant: {message.text}")
        else:
            formatted.append(f"user: {message.text}")

    if exclude_last_user_message and formatted and formatted[-1].startswith("user:"):
        formatted.pop()

    return formatted


async def process_message(phone: str, message: str, db: Session | None = None) -> str:
    """Run full WhatsApp message processing pipeline for a single incoming message."""
    owns_session = db is None
    if db is None:
        db = SessionLocal()

    repository = ConversationRepository(db)
    lead_service = LeadService(db)
    crm_service = CRMService()

    try:
        # 1. get_or_create_conversation(phone)
        conversation = repository.get_or_create_conversation(user_phone=phone)
        # 2. save user message
        repository.add_message(conversation_id=conversation.id, sender=MessageSender.USER, text=message)

        lead = lead_service.get_or_create_lead(conversation_id=conversation.id, phone=phone)

        # 3. extract entities from message
        extracted = await asyncio.to_thread(extract_entities, message)
        # 4. update lead with latest intent before any handover gate
        lead_service.update_lead_from_extracted(lead=lead, extracted=extracted)

        # 5. if conversation.status == handover
        if conversation.status == ConversationStatus.HANDOVER:
            if should_resume_bot_from_handover(message_text=message, lead=lead):
                conversation.status = ConversationStatus.ACTIVE
                db.add(conversation)
                db.commit()
            else:
                try:
                    await crm_service.add_timeline_comment(lead, message)
                except Exception:
                    logger.exception("Failed to add timeline comment while conversation is in handover")
                db.add(lead)
                db.commit()
                return "Ваше сообщение передано менеджеру."

        # 6. get conversation history
        history = _format_history_for_agent(
            repository=repository,
            conversation_id=conversation.id,
            exclude_last_user_message=True,
        )

        # 7. check handover
        handover = should_handover_to_manager(conversation=conversation, lead=lead, message_text=message)

        # 8. if handover
        if handover:
            reply = await perform_handover(conversation=conversation, lead=lead, crm_service=crm_service)
            history_for_crm = _format_history_for_agent(
                repository=repository,
                conversation_id=conversation.id,
                exclude_last_user_message=False,
            )
            try:
                await crm_service.sync_conversation_context(lead, history_for_crm)
                await crm_service.upsert_lead(lead)
                await crm_service.add_timeline_comment(lead, message)
            except Exception:
                logger.exception("CRM sync failed during handover pipeline")
            repository.add_message(conversation_id=conversation.id, sender=MessageSender.BOT, text=reply)
            db.add(lead)
            db.add(conversation)
            db.commit()
            return reply

        # 9. call AI agent
        reply = await asyncio.to_thread(run_agent, message, history)
        # 10. save bot message
        repository.add_message(conversation_id=conversation.id, sender=MessageSender.BOT, text=reply)
        # 11. create/update Bitrix24 lead
        try:
            await crm_service.upsert_lead(lead)
        except Exception:
            logger.exception("CRM upsert failed, returning bot reply without CRM confirmation")
        db.add(lead)
        db.commit()
        # 12. return bot response
        return reply
    finally:
        if owns_session:
            db.close()
