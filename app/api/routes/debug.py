from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Conversation, Lead
from app.database.repositories import ConversationRepository
from app.database.session import get_db
from app.services.property_service import PropertyService

router = APIRouter(prefix="/debug", tags=["debug"])


def _serialize_decimal(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


@router.get("/conversations")
def debug_conversations(db: Session = Depends(get_db)) -> list[dict]:
    items = list(db.scalars(select(Conversation).order_by(Conversation.created_at.desc(), Conversation.id.desc())).all())
    return [
        {
            "id": item.id,
            "user_phone": item.user_phone,
            "status": item.status.value,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in items
    ]


@router.get("/conversations/{conversation_id}")
def debug_conversation_details(conversation_id: int, db: Session = Depends(get_db)) -> dict:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    repository = ConversationRepository(db)
    messages = repository.get_conversation_messages(conversation_id)

    return {
        "conversation": {
            "id": conversation.id,
            "user_phone": conversation.user_phone,
            "status": conversation.status.value,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
        },
        "messages": [
            {
                "id": message.id,
                "sender": message.sender.value,
                "text": message.text,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            for message in messages
        ],
    }


@router.get("/leads")
def debug_leads(db: Session = Depends(get_db)) -> list[dict]:
    items = list(db.scalars(select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc())).all())
    return [
        {
            "id": item.id,
            "conversation_id": item.conversation_id,
            "phone": item.phone,
            "name": item.name,
            "budget": _serialize_decimal(item.budget),
            "rooms": item.rooms,
            "district": item.district,
            "residential_complex": item.residential_complex,
            "purchase_purpose": item.purchase_purpose.value if item.purchase_purpose else None,
            "bitrix_lead_id": item.bitrix_lead_id,
            "handover_required": item.handover_required,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in items
    ]


@router.get("/properties")
def debug_properties() -> list[dict]:
    service = PropertyService()
    return [item.model_dump() for item in service.search_properties()]
