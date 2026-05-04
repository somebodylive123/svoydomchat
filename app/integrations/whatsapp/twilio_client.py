from __future__ import annotations

import httpx

from app.integrations.whatsapp.base import WhatsAppClient


class TwilioWhatsAppClient(WhatsAppClient):
    def __init__(self, *, account_sid: str, auth_token: str, from_number: str) -> None:
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send_message(self, *, to_phone: str, message: str) -> None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "From": self.from_number,
            "To": to_phone,
            "Body": message,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, data=data, auth=(self.account_sid, self.auth_token))
            response.raise_for_status()
