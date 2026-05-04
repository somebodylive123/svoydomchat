from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from urllib.parse import parse_qs

from app.api.schemas.whatsapp import WhatsAppWebhookRequest, WhatsAppWebhookResponse
from app.bot.message_processor import process_message
from app.config import settings
from app.database.repositories import ConversationRepository
from app.database.session import get_db
from app.services.whatsapp_service import get_whatsapp_client

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/whatsapp", response_model=None)
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    content_type = request.headers.get("content-type", "")
    is_twilio = "application/x-www-form-urlencoded" in content_type

    if is_twilio:
        raw_body = (await request.body()).decode("utf-8")
        parsed = parse_qs(raw_body)
        phone = parsed.get("From", [""])[0].strip()
        message = parsed.get("Body", [""])[0].strip()
    else:
        body = await request.json()
        payload = WhatsAppWebhookRequest(**body)
        phone = payload.phone
        message = payload.message

    reply = await process_message(phone=phone, message=message, db=db)

    repository = ConversationRepository(db)
    conversation = repository.get_or_create_conversation(user_phone=phone)

    if is_twilio:
        if settings.whatsapp_provider == "twilio":
            client = get_whatsapp_client()
            await client.send_message(to_phone=phone, message=reply)
            return Response(status_code=204)
        return Response(content=f"<Response><Message>{reply}</Message></Response>", media_type="application/xml")

    return JSONResponse(
        content=WhatsAppWebhookResponse(reply=reply, conversation_status=conversation.status.value).model_dump()
    )
