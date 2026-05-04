from types import SimpleNamespace

from app.integrations.bitrix24.mock_client import MockBitrix24Client
from app.integrations.bitrix24.real_client import RealBitrix24Client
from app.services import crm_service


def test_build_client_uses_real_when_webhook_url_is_set(monkeypatch) -> None:
    monkeypatch.setattr(
        crm_service,
        "settings",
        SimpleNamespace(bitrix_mode="mock", bitrix_webhook_url="https://example.bitrix24.kz/rest/1/abc"),
    )

    client = crm_service._build_client()

    assert isinstance(client, RealBitrix24Client)


def test_build_client_uses_mock_without_webhook_url(monkeypatch) -> None:
    monkeypatch.setattr(crm_service, "settings", SimpleNamespace(bitrix_mode="mock", bitrix_webhook_url=None))

    client = crm_service._build_client()

    assert isinstance(client, MockBitrix24Client)
