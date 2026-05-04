from app.bot import message_processor
from app.bot.handover import should_handover_to_manager
from app.database.models import Conversation, ConversationStatus, Lead
import asyncio


def _conversation(status: ConversationStatus = ConversationStatus.ACTIVE) -> Conversation:
    return Conversation(user_phone="+7700000000", status=status)


def _lead(**kwargs) -> Lead:
    base = {
        "conversation_id": 1,
        "phone": "+7700000000",
        "budget": None,
        "rooms": None,
        "district": None,
        "residential_complex": None,
        "handover_required": False,
    }
    base.update(kwargs)
    return Lead(**base)


def test_handover_when_wants_manager_true() -> None:
    conversation = _conversation()
    lead = _lead(handover_required=True)

    assert should_handover_to_manager(conversation=conversation, lead=lead, message_text="") is True


def test_no_handover_only_because_lead_qualified() -> None:
    conversation = _conversation()
    lead = _lead(budget=45_000_000, rooms=2, district="Ботанический сад")

    assert should_handover_to_manager(conversation=conversation, lead=lead, message_text="Ищу варианты") is False


def test_handover_by_keyword_even_when_lead_not_qualified() -> None:
    conversation = _conversation()
    lead = _lead()

    assert should_handover_to_manager(conversation=conversation, lead=lead, message_text="Свяжите с менеджером") is True


def test_handover_when_user_selects_specific_apartment() -> None:
    conversation = _conversation()
    lead = _lead()

    assert (
        should_handover_to_manager(
            conversation=conversation,
            lead=lead,
            message_text="Вот эту квартиру хотел бы рассмотреть: https://mock.svoydom.kz/properties/ast-001",
        )
        is True
    )


def test_no_handover_when_user_asks_for_other_options() -> None:
    conversation = _conversation()
    lead = _lead()

    assert (
        should_handover_to_manager(
            conversation=conversation,
            lead=lead,
            message_text="Хочу посмотреть другие варианты в районе Есиль до 45 миллионов",
        )
        is False
    )


def test_handover_when_user_confirms_choice() -> None:
    conversation = _conversation()
    lead = _lead()

    assert should_handover_to_manager(conversation=conversation, lead=lead, message_text="Да, выбираю ее") is True


def test_bot_does_not_call_ai_after_handover(monkeypatch) -> None:
    class FakeConversation:
        id = 1
        status = ConversationStatus.HANDOVER

    class FakeLead:
        bitrix_lead_id = None
        handover_required = False

    class FakeRepository:
        def __init__(self, db):
            pass

        def get_or_create_conversation(self, user_phone: str):
            return FakeConversation()

        def add_message(self, conversation_id: int, sender, text: str):
            return None

    class FakeLeadService:
        def __init__(self, db):
            pass

        def get_or_create_lead(self, conversation_id: int, phone: str):
            return FakeLead()

        def update_lead_from_extracted(self, lead, extracted):
            return lead

    class FakeCRMService:
        async def add_timeline_comment(self, lead, comment: str):
            return None

    monkeypatch.setattr(message_processor, "ConversationRepository", FakeRepository)
    monkeypatch.setattr(message_processor, "LeadService", FakeLeadService)
    monkeypatch.setattr(message_processor, "CRMService", lambda: FakeCRMService())

    def _fail_run_agent(*args, **kwargs):
        raise AssertionError("run_agent must not be called in handover status")

    monkeypatch.setattr(message_processor, "run_agent", _fail_run_agent)

    fake_db = type("FakeDB", (), {"add": lambda self, obj: None, "commit": lambda self: None})()
    reply = asyncio.run(message_processor.process_message(phone="+7700000000", message="привет", db=fake_db))

    assert reply == "Ваше сообщение передано менеджеру."


def test_resume_from_handover_on_new_search_request() -> None:
    lead = _lead(handover_required=False)

    from app.bot.handover import should_resume_bot_from_handover

    assert should_resume_bot_from_handover(
        message_text="Ищу 2-комнатную квартиру в районе Ботанического сада до 45 млн",
        lead=lead,
    ) is True


def test_do_not_resume_from_handover_on_manager_request() -> None:
    lead = _lead(handover_required=False)

    from app.bot.handover import should_resume_bot_from_handover

    assert should_resume_bot_from_handover(message_text="Свяжите с менеджером", lead=lead) is False


def test_handover_lead_flag_is_reset_before_handover_gate(monkeypatch) -> None:
    class FakeConversation:
        id = 1
        status = ConversationStatus.HANDOVER

    class FakeLead:
        bitrix_lead_id = None
        handover_required = True

    class FakeRepository:
        def __init__(self, db):
            pass

        def get_or_create_conversation(self, user_phone: str):
            return FakeConversation()

        def add_message(self, conversation_id: int, sender, text: str):
            return None

        def get_conversation_messages(self, conversation_id: int):
            return []

    class FakeLeadService:
        def __init__(self, db):
            pass

        def get_or_create_lead(self, conversation_id: int, phone: str):
            return FakeLead()

        def update_lead_from_extracted(self, lead, extracted):
            lead.handover_required = extracted.wants_manager
            return lead

    class FakeCRMService:
        async def add_timeline_comment(self, lead, comment: str):
            return None

        async def upsert_lead(self, lead):
            return None

    class Extracted:
        wants_manager = False

    monkeypatch.setattr(message_processor, "ConversationRepository", FakeRepository)
    monkeypatch.setattr(message_processor, "LeadService", FakeLeadService)
    monkeypatch.setattr(message_processor, "CRMService", lambda: FakeCRMService())
    monkeypatch.setattr(message_processor, "extract_entities", lambda text: Extracted())
    monkeypatch.setattr(message_processor, "run_agent", lambda user_message, conversation_history=None: "Нашёл вариант")

    reply = asyncio.run(
        message_processor.process_message(
            phone="+7700000000",
            message="Ищу 2-комнатную квартиру в районе Ботанического сада до 45 млн",
            db=type("FakeDB", (), {"add": lambda self, obj: None, "commit": lambda self: None})(),
        )
    )

    assert reply == "Нашёл вариант"
