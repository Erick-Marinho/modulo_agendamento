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

@router.post("/test", status_code=status.HTTP_200_OK)
async def test_endpoint():
    """
    Endpoint de teste para verificar se a API está funcionando
    """
    try:
        logger.info("=== TESTE SIMPLES ===")
        return {"status": "OK", "message": "Endpoint funcionando"}
    except Exception as e:
        logger.error(f"Erro no teste: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-agent", status_code=status.HTTP_200_OK)
async def test_agent(agent = Depends(get_message_agent)):
    """
    Endpoint de teste para verificar se o agente está funcionando
    """
    try:
        logger.info("=== TESTE DO AGENTE ===")
        
        # Teste básico sem usar o MessageService
        test_state = {
            "message": "teste",
            "phone_number": "+123456789",
            "message_id": "test_id",
            "messages": [HumanMessage(content="teste")],
            "next_step": "",
            "conversation_context": None,
            "extracted_scheduling_details": None,
            "missing_fields": None,
            "awaiting_user_input": None
        }
        
        config = {"configurable": {"thread_id": "+123456789"}}
        
        logger.info("Executando agente diretamente...")
        result = await agent.ainvoke(test_state, config=config)
        logger.info(f"Agente executado. Resultado: {len(result.get('messages', []))} mensagens")
        
        return {"status": "OK", "messages_count": len(result.get('messages', []))}
        
    except Exception as e:
        logger.error(f"Erro no teste do agente: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))