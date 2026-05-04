from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app


def test_whatsapp_webhook_returns_reply(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    async def _fake_process_message(phone, message, db=None):
        return "Тестовый ответ"

    monkeypatch.setattr(
        "app.api.routes.whatsapp.process_message",
        _fake_process_message,
    )

    client = TestClient(app)
    response = client.post(
        "/webhooks/whatsapp",
        json={"phone": "+7700000000", "message": "Привет"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"] == "Тестовый ответ"


def test_twilio_sandbox_webhook_returns_twiml(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    async def _fake_process_message(phone, message, db=None):
        return "Twilio reply"

    monkeypatch.setattr("app.api.routes.whatsapp.process_message", _fake_process_message)

    client = TestClient(app)
    response = client.post(
        "/webhooks/whatsapp",
        data={"From": "whatsapp:+7700000000", "Body": "Привет"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "<Response><Message>Twilio reply</Message></Response>" == response.text
