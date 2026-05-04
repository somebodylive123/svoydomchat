from __future__ import annotations

from app.core.logger import logger
from app.integrations.whatsapp.base import WhatsAppClient


class MockWhatsAppClient(WhatsAppClient):
    async def send_message(self, *, to_phone: str, message: str) -> None:
        logger.info("Mock WhatsApp send to %s: %s", to_phone, message)
