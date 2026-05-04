from __future__ import annotations

from app.config import settings
from app.integrations.whatsapp import MockWhatsAppClient, WhatsAppClient, TwilioWhatsAppClient


def get_whatsapp_client() -> WhatsAppClient:
    if settings.whatsapp_provider == "twilio":
        if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_whatsapp_from:
            raise ValueError("Twilio WhatsApp is enabled but credentials are incomplete")
        return TwilioWhatsAppClient(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            from_number=settings.twilio_whatsapp_from,
        )
    return MockWhatsAppClient()
