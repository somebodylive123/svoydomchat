from decimal import Decimal

from app.bot.entity_extractor import LeadExtractedData, PurchasePurpose as ExtractPurpose
from app.database.models import Lead
from app.services.lead_service import is_qualified_lead


def test_is_qualified_lead_true_when_all_required_fields_present() -> None:
    lead = Lead(phone="77001112233", budget=Decimal("45000000"), rooms=2, district="Ботанический сад")
    assert is_qualified_lead(lead) is True


def test_is_qualified_lead_false_without_location() -> None:
    lead = Lead(phone="77001112233", budget=Decimal("45000000"), rooms=2)
    assert is_qualified_lead(lead) is False


def test_lead_extracted_data_unknown_purchase_purpose_supported() -> None:
    data = LeadExtractedData(purchase_purpose=ExtractPurpose.UNKNOWN)
    assert data.purchase_purpose == ExtractPurpose.UNKNOWN