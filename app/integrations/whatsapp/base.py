from __future__ import annotations

from abc import ABC, abstractmethod


class WhatsAppClient(ABC):
    @abstractmethod
    async def send_message(self, *, to_phone: str, message: str) -> None:
        """Send outgoing WhatsApp message to user."""
