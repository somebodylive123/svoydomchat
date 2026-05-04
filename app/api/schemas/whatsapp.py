from pydantic import BaseModel, Field


class WhatsAppWebhookRequest(BaseModel):
    phone: str = Field(..., examples=["+77001234567"])
    message: str = Field(..., min_length=1, examples=["Ищу 2-комнатную квартиру до 45 млн"])


class TwilioWebhookRequest(BaseModel):
    from_phone: str
    body: str


class WhatsAppWebhookResponse(BaseModel):
    reply: str
    conversation_status: str
