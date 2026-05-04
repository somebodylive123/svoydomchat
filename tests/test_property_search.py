from app.services.property_service import PropertyService
from app.bot.agent import run_agent


def test_search_by_district() -> None:
    service = PropertyService()
    items = service.search_properties(district="ботанический парк")

    assert items
    assert all(item.district == "Ботанический сад" for item in items)


def test_search_by_rooms() -> None:
    service = PropertyService()
    items = service.search_properties(rooms=2)

    assert items
    assert all(item.rooms == 2 for item in items)


def test_search_by_budget() -> None:
    service = PropertyService()
    items = service.search_properties(max_budget=40_000_000)

    assert items
    assert all(item.price <= 40_000_000 for item in items)


def test_search_empty_result() -> None:
    service = PropertyService()
    items = service.search_properties(district="Несуществующий район")

    assert items == []


def test_run_agent_returns_matching_properties_for_search_query() -> None:
    reply = run_agent("Ищу 2-комнатную квартиру в районе Ботанического сада, бюджет до 45 млн, для жизни")

    assert "ast-001" in reply
    assert "ast-006" in reply
    assert "ast-007" in reply
    assert "ast-005" not in reply


def test_run_agent_returns_relaxed_budget_options() -> None:
    reply = run_agent("Ищу 2-комнатную квартиру в районе Ботанического парка, бюджет до 40 млн")

    assert "выше указанного бюджета" in reply
    assert "ast-006" in reply


def test_run_agent_search_by_residential_complex() -> None:
    reply = run_agent("Ищу квартиру в жк Nova City")

    assert "ast-004" in reply


def test_run_agent_search_by_esil_alias() -> None:
    reply = run_agent("Ищу 2-комнатную в есильском районе")

    assert "ast-003" in reply


def test_run_agent_adds_hint_for_missing_room_type_due_to_budget() -> None:
    reply = run_agent("Ищу квартиру в районе Ботанического сада, бюджет до 60 млн")

    assert "ast-001" in reply
    assert "ast-002" in reply
    assert "выше бюджета" in reply


def test_selection_intent_does_not_trigger_new_property_search() -> None:
    reply = run_agent("да, я выбираю эту квартиру: 2-комнатная квартира у Ботанического сада: 43 200 000 ₸, 62.3 м², https://mock.svoydom.kz/properties/ast-006")

    assert "фиксирую выбор квартиры" in reply
    assert "Нашёл подходящие варианты" not in reply
