from __future__ import annotations

from abc import ABC, abstractmethod

from app.database.models import Lead


class Bitrix24ClientBase(ABC):
    @abstractmethod
    async def create_lead(self, lead: Lead) -> str:
        raise NotImplementedError

    @abstractmethod
    async def update_lead(self, lead: Lead) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_timeline_comment(self, lead_id: str, comment: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def notify_manager(self, lead: Lead, reason: str) -> None:
        raise NotImplementedError
