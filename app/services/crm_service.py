from __future__ import annotations

import re

from app.config import settings
from app.core.logger import logger
from app.database.models import Lead
from app.integrations.bitrix24.base import Bitrix24ClientBase
from app.integrations.bitrix24.mock_client import MockBitrix24Client
from app.integrations.bitrix24.real_client import RealBitrix24Client


class CRMService:
    def __init__(self, client: Bitrix24ClientBase | None = None):
        self.client = client or _build_client()

    async def upsert_lead(self, lead: Lead) -> None:
        if lead.bitrix_lead_id and _is_valid_bitrix_lead_id(lead.bitrix_lead_id):
            await self.client.update_lead(lead)
            return

        if lead.bitrix_lead_id and not _is_valid_bitrix_lead_id(lead.bitrix_lead_id):
            logger.warning("Invalid Bitrix lead id '%s'; creating a new lead", lead.bitrix_lead_id)
            lead.bitrix_lead_id = None

        lead.bitrix_lead_id = await self.client.create_lead(lead)

    async def add_timeline_comment(self, lead: Lead, comment: str) -> None:
        if not lead.bitrix_lead_id:
            lead.bitrix_lead_id = await self.client.create_lead(lead)
        await self.client.add_timeline_comment(lead.bitrix_lead_id, comment)

    async def notify_manager(self, lead: Lead, reason: str) -> None:
        if not lead.bitrix_lead_id:
            lead.bitrix_lead_id = await self.client.create_lead(lead)
        await self.client.notify_manager(lead, reason)

    async def sync_conversation_context(self, lead: Lead, messages: list[str]) -> None:
        if not lead.bitrix_lead_id:
            lead.bitrix_lead_id = await self.client.create_lead(lead)
        if not messages:
            return
        transcript = "\n".join(messages[-10:])
        comment = (
            "[DIALOG_SYNC] История диалога:\n"
            f"{transcript}\n\n"
            f"[LEAD_DATA] budget={lead.budget}; rooms={lead.rooms}; district={lead.district}; "
            f"rc={lead.residential_complex}; purpose={lead.purchase_purpose}"
        )
        await self.client.add_timeline_comment(lead.bitrix_lead_id, comment)


def _build_client() -> Bitrix24ClientBase:
    mode = (settings.bitrix_mode or "").strip().lower()

    if settings.bitrix_webhook_url:
        if mode != "real":
            logger.warning(
                "BITRIX_WEBHOOK_URL is set, forcing real Bitrix24 client (BITRIX_MODE=%s)",
                settings.bitrix_mode,
            )
        return RealBitrix24Client(webhook_url=settings.bitrix_webhook_url)

    if mode == "real":
        raise ValueError("BITRIX_WEBHOOK_URL must be set when BITRIX_MODE=real")

    logger.warning("Bitrix24 mock mode is enabled: leads are not sent to real Bitrix24")
    return MockBitrix24Client()


def _is_valid_bitrix_lead_id(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", value.strip()))
