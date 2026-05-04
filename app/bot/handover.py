from __future__ import annotations

import re

from app.database.models import Conversation, ConversationStatus, Lead
from app.services.crm_service import CRMService


HANDOVER_KEYWORDS = re.compile(
    r"(хотел\s+бы\s+рассмотреть\s+(эту|этот)\s+квартир\w*|"
    r"вот\s+эту\s+квартир\w*|"
    r"запишите\s+на\s+просмотр|свяжите\s+с\s+менеджером|"
    r"бер[еу]\s+эту\s+квартир\w*|"
    r"выбираю\s+е[её])",
    re.IGNORECASE,
)

CONTINUE_SEARCH_KEYWORDS = re.compile(
    r"(друг[а-я]*\s+вариант|друг[а-я]*\s+квартир|ещ[её]\s+вариант|покажи\s+ещ[её]|"
    r"хочу\s+посмотреть\s+друг[а-я]*|посмотреть\s+друг[а-я]*)",
    re.IGNORECASE,
)

HANDOVER_REPLY = "Передал ваш запрос менеджеру. Он свяжется с вами и уточнит детали."


def should_handover_to_manager(*, conversation: Conversation, lead: Lead, message_text: str) -> bool:
    if conversation.status == ConversationStatus.HANDOVER:
        return True

    if lead.handover_required:
        return True

    if CONTINUE_SEARCH_KEYWORDS.search(message_text):
        return False

    return bool(HANDOVER_KEYWORDS.search(message_text))


async def perform_handover(*, conversation: Conversation, lead: Lead, crm_service: CRMService) -> str:
    conversation.status = ConversationStatus.HANDOVER
    await crm_service.notify_manager(lead=lead, reason="Пользователь готов к передаче менеджеру")
    return HANDOVER_REPLY


def should_resume_bot_from_handover(*, message_text: str, lead: Lead) -> bool:
    """Allow bot to resume when user sends a fresh search request after handover."""
    lowered = message_text.lower()

    explicit_manager_request = bool(HANDOVER_KEYWORDS.search(lowered))
    has_search_intent = any(token in lowered for token in ("ищу", "квартир", "комнат", "жк", "район", "бюджет", "до "))

    return conversation_reset_candidate(lead=lead) and has_search_intent and not explicit_manager_request


def conversation_reset_candidate(*, lead: Lead) -> bool:
    return not bool(getattr(lead, "handover_required", False))
