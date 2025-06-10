import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto.message_request_dto import MessageRequestPayload
from app.application.agents.message_agent_builder import get_message_agent
from app.application.services.message_service import MessageService

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_message_service_dependency(agent=Depends(get_message_agent)):
    return MessageService(agent=agent)


@router.post("/", status_code=status.HTTP_200_OK)
async def send_message(
    message_request: MessageRequestPayload,
    message_service: MessageService = Depends(get_message_service_dependency),
):
    """
    Endpoint para processar a mensagem recebida e disparar o envio da resposta
    via N8N. O corpo da resposta indica o status do envio ao webhook.
    """
    try:
        # O serviço agora lida com o envio da mensagem
        n8n_result = await message_service.process_message(message_request)

        logger.info(f"Resultado do envio para o N8N: {n8n_result}")

        # Se houve um erro no envio para o N8N, retornamos um erro interno
        if "error" in n8n_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Falha ao enviar a resposta para o webhook: {n8n_result.get('details', 'Erro desconhecido')}",
            )

        # Retornamos o status do envio para o N8N como sucesso
        return {
            "status": "message_processed_and_sent",
            "n8n_response": n8n_result,
        }

    except HTTPException:
        # Re-lança exceções HTTP que já foram tratadas
        raise

    except Exception as e:
        logger.error(
            f"Erro inesperado no endpoint /message: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno ao processar a mensagem.",
        )
