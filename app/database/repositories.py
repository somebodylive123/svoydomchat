from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Conversation, Lead, Message, MessageSender


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_conversation(self, user_phone: str) -> Conversation:
        stmt = select(Conversation).where(Conversation.user_phone == user_phone)
        conversation = self.db.scalar(stmt)
        if conversation:
            return conversation

        conversation = Conversation(user_phone=user_phone)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def add_message(self, conversation_id: int, sender: MessageSender, text: str) -> Message:
        message = Message(conversation_id=conversation_id, sender=sender, text=text)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_conversation_messages(self, conversation_id: int) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        return list(self.db.scalars(stmt).all())


class LeadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_lead(self, conversation_id: int, phone: str) -> Lead:
        stmt = select(Lead).where(Lead.conversation_id == conversation_id)
        lead = self.db.scalar(stmt)
        if lead:
            return lead

        lead = Lead(conversation_id=conversation_id, phone=phone)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update_lead(self, lead: Lead, **updates) -> Lead:
        for field, value in updates.items():
            if hasattr(lead, field) and value is not None:
                setattr(lead, field, value)

        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead
