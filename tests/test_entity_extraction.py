from app.bot.entity_extractor import PurchasePurpose, extract_entities
from app.bot import entity_extractor


def test_extract_rooms_and_budget() -> None:
    data = extract_entities("Ищу 2-комнатную до 45 млн")
    assert data.rooms == 2


def test_extract_purchase_purpose_investment() -> None:
    data = extract_entities("для инвестиции")
    assert data.purchase_purpose == PurchasePurpose.INVESTMENT


def test_extract_wants_manager() -> None:
    data = extract_entities("свяжите с менеджером")
    assert data.wants_manager is True


def test_extract_district_from_message() -> None:
    data = extract_entities("Ищу квартиру в районе Ботанического сада")
    assert data.district == "Ботанический сад"


def test_extract_budget_million_suffix() -> None:
    data = extract_entities("Бюджет 45 млн")
    assert data.budget == 45_000_000


def test_normalize_district_name_from_llm_style_value() -> None:
    normalized = entity_extractor._normalize_district_name("Ботанического сада")
    assert normalized == "Ботанический сад"


def test_extract_residential_complex_from_message() -> None:
    data = extract_entities("Ищу квартиру в жк Nova City")
    assert data.residential_complex == "Nova City"


def test_extract_almaty_district_variation() -> None:
    data = extract_entities("Ищу квартиру в алматинском районе")
    assert data.district == "Алматы"


def test_extract_baikonyr_district_variation() -> None:
    data = extract_entities("Нужна квартира в районе Байконур")
    assert data.district == "Байконыр"


def test_astana_citywide_query_does_not_set_district() -> None:
    data = extract_entities("Найди мне квартиры по Астане до 45 млн")
    assert data.district is None