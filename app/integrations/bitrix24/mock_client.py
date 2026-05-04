from __future__ import annotations

from app.core.logger import logger
from app.database.models import Lead
from app.integrations.bitrix24.base import Bitrix24ClientBase


class MockBitrix24Client(Bitrix24ClientBase):
    async def create_lead(self, lead: Lead) -> str:
        fake_id = lead.bitrix_lead_id or f"mock-lead-{lead.conversation_id}"
        logger.info("[BITRIX MOCK] create_lead payload=%s fake_id=%s", _lead_payload(lead), fake_id)
        return fake_id

    async def update_lead(self, lead: Lead) -> None:
        logger.info("[BITRIX MOCK] update_lead payload=%s", _lead_payload(lead))

    async def add_timeline_comment(self, lead_id: str, comment: str) -> None:
        logger.info("[BITRIX MOCK] add_timeline_comment lead_id=%s comment=%s", lead_id, comment)

    async def notify_manager(self, lead: Lead, reason: str) -> None:
        logger.info("[BITRIX MOCK] notify_manager lead_id=%s reason=%s", lead.bitrix_lead_id, reason)


def _lead_payload(lead: Lead) -> dict[str, object | None]:
    return {
        "phone": lead.phone,
        "budget": str(lead.budget) if lead.budget is not None else None,
        "rooms": lead.rooms,
        "district": lead.district,
        "residential_complex": lead.residential_complex,
        "purchase_purpose": lead.purchase_purpose.value if lead.purchase_purpose else None,
    }
