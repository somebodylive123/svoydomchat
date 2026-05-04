from __future__ import annotations
import json
import httpx

from app.database.models import Lead
from app.integrations.bitrix24.base import Bitrix24ClientBase


class RealBitrix24Client(Bitrix24ClientBase):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.rstrip("/")

    async def create_lead(self, lead: Lead) -> str:
        payload = {
            "fields": {
                "TITLE": f"Lead from WhatsApp {lead.phone}",
                "PHONE": [{"VALUE": lead.phone, "VALUE_TYPE": "WORK"}],
                "COMMENTS": self._lead_comment(lead),
            }
        }
        response = await self._post("crm.lead.add.json", payload)
        result = response.get("result")
        return str(result)

    async def update_lead(self, lead: Lead) -> None:
        if not lead.bitrix_lead_id:
            return

        payload = {
            "id": lead.bitrix_lead_id,
            "fields": {
                "COMMENTS": self._lead_comment(lead),
            },
        }
        await self._post("crm.lead.update.json", payload)

    async def add_timeline_comment(self, lead_id: str, comment: str) -> None:
        payload = {
            "fields": {
                "ENTITY_ID": lead_id,
                "ENTITY_TYPE": "lead",
                "ENTITY_TYPE_ID": 1,
                "COMMENT": comment,
            }
        }
        await self._post("crm.timeline.comment.add.json", payload)

    async def notify_manager(self, lead: Lead, reason: str) -> None:
        if not lead.bitrix_lead_id:
            return
        await self.add_timeline_comment(lead.bitrix_lead_id, f"[HANDOVER] {reason}")

    async def _post(self, method: str, payload: dict[str, object]) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.webhook_url}/{method}",
                data=self._bitrix_form_payload(payload),
            )
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"Bitrix24 HTTP {response.status_code} for {method}: {response.text}",
                    request=response.request,
                    response=response,
                )
            data = response.json()
            if "error" in data:
                raise RuntimeError(f"Bitrix24 error: {data['error']} {data.get('error_description', '')}")
            return data

    def _bitrix_form_payload(self, payload: dict[str, object]) -> dict[str, str]:
        encoded: dict[str, str] = {}
        for key, value in payload.items():
            self._flatten_form_value(prefix=key, value=value, out=encoded)
        return encoded

    def _flatten_form_value(self, prefix: str, value: object, out: dict[str, str]) -> None:
        if isinstance(value, dict):
            for key, nested_value in value.items():
                self._flatten_form_value(prefix=f"{prefix}[{key}]", value=nested_value, out=out)
            return
        if isinstance(value, list):
            for idx, nested_value in enumerate(value):
                self._flatten_form_value(prefix=f"{prefix}[{idx}]", value=nested_value, out=out)
            return
        out[prefix] = "" if value is None else str(value)

    def _lead_comment(self, lead: Lead) -> str:
        return (
            f"budget={lead.budget}; rooms={lead.rooms}; district={lead.district}; "
            f"rc={lead.residential_complex}; purpose={lead.purchase_purpose}"
        )
