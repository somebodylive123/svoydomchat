import json
from pathlib import Path

from app.core.astana_districts import normalize_astana_district
from app.integrations.svoydom.base import BaseSvoydomClient
from app.integrations.svoydom.schemas import Property


class MockSvoydomClient(BaseSvoydomClient):
    def __init__(self, data_file: str = "app/data/mock_properties.json"):
        self.data_file = Path(data_file)

    def _load_properties(self) -> list[Property]:
        raw_data = json.loads(self.data_file.read_text(encoding="utf-8"))
        return [Property(**item) for item in raw_data]

    def search_properties(
        self,
        district: str | None = None,
        residential_complex: str | None = None,
        rooms: int | None = None,
        max_budget: int | None = None,
    ) -> list[Property]:
        properties = self._load_properties()

        if district:
            district_lc = district.strip().lower()
            district_norm = normalize_astana_district(district)
            properties = [
                p
                for p in properties
                if (
                    normalize_astana_district(p.district) == district_norm
                    or district_lc in p.district.lower()
                    or p.district.lower() in district_lc
                )
            ]

        if residential_complex:
            rc_lc = residential_complex.strip().lower()
            properties = [
                p
                for p in properties
                if rc_lc in p.residential_complex.lower() or p.residential_complex.lower() in rc_lc
            ]

        if rooms is not None:
            properties = [p for p in properties if p.rooms == rooms]

        if max_budget is not None:
            properties = [p for p in properties if p.price <= max_budget]

        return properties
