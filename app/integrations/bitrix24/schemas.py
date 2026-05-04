from __future__ import annotations

from pydantic import BaseModel, Field


class BitrixLeadFields(BaseModel):
    title: str = Field(..., alias="TITLE")
    name: str | None = Field(default=None, alias="NAME")
    phone: list[dict[str, str]] = Field(default_factory=list, alias="PHONE")
    comments: str | None = Field(default=None, alias="COMMENTS")


class CreateLeadRequest(BaseModel):
    fields: BitrixLeadFields


class UpdateLeadRequest(BaseModel):
    id: str | int
    fields: dict[str, object]


class TimelineCommentFields(BaseModel):
    entity_id: str | int = Field(..., alias="ENTITY_ID")
    entity_type: str = Field(default="lead", alias="ENTITY_TYPE")
    comment: str = Field(..., alias="COMMENT")


class AddTimelineCommentRequest(BaseModel):
    fields: TimelineCommentFields
