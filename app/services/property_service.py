from app.integrations.svoydom.mock_client import MockSvoydomClient
from app.integrations.svoydom.schemas import Property


class PropertyService:
    def __init__(self, client: MockSvoydomClient | None = None):
        self.client = client or MockSvoydomClient()

    def search_properties(
        self,
        district: str | None = None,
        residential_complex: str | None = None,
        rooms: int | None = None,
        max_budget: int | None = None,
    ) -> list[Property]:
        return self.client.search_properties(
            district=district,
            residential_complex=residential_complex,
            rooms=rooms,
            max_budget=max_budget,
        )
