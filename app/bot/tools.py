from __future__ import annotations

from langchain_core.tools import tool

from app.services.property_service import PropertyService


@tool("search_properties")
def search_properties(
    district: str | None = None,
    residential_complex: str | None = None,
    rooms: int | None = None,
    max_budget: int | None = None,
) -> list[dict]:
    """Find properties by district/complex, room count, and maximum budget."""
    service = PropertyService()
    items = service.search_properties(
        district=district,
        residential_complex=residential_complex,
        rooms=rooms,
        max_budget=max_budget,
    )

    return [item.model_dump() for item in items]
