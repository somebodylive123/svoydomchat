from abc import ABC, abstractmethod

from app.integrations.svoydom.schemas import Property


class BaseSvoydomClient(ABC):
    @abstractmethod
    def search_properties(
        self,
        district: str | None = None,
        residential_complex: str | None = None,
        rooms: int | None = None,
        max_budget: int | None = None,
    ) -> list[Property]:
        """Return properties that match given filters."""
