import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto.message_request_dto import MessageRequestPayload
from app.application.services.message_service import MessageService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", status_code=status.HTTP_200_OK)
async def send_message(message_request: MessageRequestPayload, message_service: MessageService = Depends(MessageService)):
    """
    Endpoint para processar a mensagem recebida
    """

    message_response = await message_service.process_message(message_request)

    logger.info(f"Mensagem processada: {message_response}")

    return message_response