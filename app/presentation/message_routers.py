import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto.message_request_dto import MessageRequestPayload
from app.application.agents.message_agent_builder import get_message_agent
from app.application.services.message_service import MessageService

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_message_service_dependency(agent = Depends(get_message_agent)):
    return MessageService(agent=agent)

@router.post("/", status_code=status.HTTP_200_OK)
async def send_message(message_request: MessageRequestPayload, message_service: MessageService = Depends(get_message_service_dependency)):
    """
    Endpoint para processar a mensagem recebida
    """

    try:
        message_response = await message_service.process_message(message_request)

        logger.info(f"Mensagem processada: {message_response}")

        return message_response
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))