from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.bot.entity_extractor import LeadExtractedData
from app.database.models import Lead, PurchasePurpose
from app.database.repositories import LeadRepository


@dataclass(slots=True)
class LeadReadiness:
    score: int
    qualified: bool


class LeadService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = LeadRepository(db)

    def get_or_create_lead(self, conversation_id: int, phone: str) -> Lead:
        return self.repository.get_or_create_lead(conversation_id=conversation_id, phone=phone)

    def update_lead_from_extracted(self, lead: Lead, extracted: LeadExtractedData) -> Lead:
        """Update lead only with non-empty values from extracted payload."""
        updates: dict[str, object] = {
            "budget": extracted.budget,
            "rooms": extracted.rooms,
            "district": _normalize_optional_text(extracted.district),
            "residential_complex": _normalize_optional_text(extracted.residential_complex),
            "handover_required": extracted.wants_manager,
        }

        purpose = _map_purchase_purpose(extracted.purchase_purpose.value)
        if purpose is not None:
            updates["purchase_purpose"] = purpose

        return self.repository.update_lead(lead, **updates)

    def get_lead_readiness(self, lead: Lead) -> LeadReadiness:
        """Calculate readiness score and qualification status."""
        score = 0
        if bool(lead.phone and lead.phone.strip()):
            score += 1
        if lead.budget is not None:
            score += 1
        if lead.rooms is not None:
            score += 1
        if bool((lead.district and lead.district.strip()) or (lead.residential_complex and lead.residential_complex.strip())):
            score += 1

        return LeadReadiness(score=score, qualified=is_qualified_lead(lead))


def is_qualified_lead(lead: Lead) -> bool:
    """Lead is qualified when required contact + intent fields are present."""
    has_phone = bool(lead.phone and lead.phone.strip())
    has_budget = lead.budget is not None
    has_rooms = lead.rooms is not None
    has_location = bool((lead.district and lead.district.strip()) or (lead.residential_complex and lead.residential_complex.strip()))

    return has_phone and has_budget and has_rooms and has_location


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _map_purchase_purpose(value: str) -> PurchasePurpose | None:
    if value == "living":
        return PurchasePurpose.LIVING
    if value == "investment":
        return PurchasePurpose.INVESTMENT
    return None
