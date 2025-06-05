import logging
import traceback

from fastapi import Depends
from langchain_core.messages import HumanMessage, AIMessage
from app.application.agents.message_agent_builder import MessageAgentBuilder
from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.dto.message_request_dto import MessageRequestPayload
from app.application.dto.message_response_dto import MessageResponsePayload
from app.infrastructure.persistence.ISaveCheckpoint import SaveCheckpointInterface
from app.infrastructure.persistence.mongodb_saver_checkpointer import MongoDBSaverCheckpointer

logger = logging.getLogger(__name__)

class MessageService:
    """
    Serviço para processar a mensagem recebida
    """

    def __init__(self, agent):
        """
        Inicializa o serviço de mensagem

        Args:
            checkpointer: SaveCheckpointInterface (MongoDBSaver oficial por padrão)
        """
        if agent is None:
            logger.error("Agente não inicializado - MessageService não pode ser inicializado")
            raise ValueError("O agente não pode ser None para o MessageService")
        
        self.message_agent = agent
        logger.info("MessageService inicializado com o agente de mensagem injetado")

    async def process_message(self, request_payload: MessageRequestPayload) -> MessageResponsePayload:
        """
        Processa a mensagem recebida

        Args:
            message: MessageRequestPayload

        Returns:
            MessageResponsePayload
        """
        try:
            logger.info(f"=== INICIANDO PROCESSAMENTO ===")
            logger.info(f"Payload recebido: {request_payload}")

            thread_id = request_payload.phone_number
            config = {"configurable": {"thread_id": thread_id}}

            initial_state: MessageAgentState = {
                "message": request_payload.message,
                "phone_number": request_payload.phone_number,
                "message_id": request_payload.message_id,
                "messages": [HumanMessage(content=request_payload.message)],
                "next_step": "",
                "conversation_context": None,
                "extracted_scheduling_details": None,
                "missing_fields": None,
                "awaiting_user_input": None
            }
            
            logger.info(f"Estado inicial criado com {len(initial_state['messages'])} mensagens")

            logger.info(f"=== EXECUTANDO AGENTE ===")
            final_state: MessageAgentState = await self.message_agent.ainvoke(initial_state, config=config)
            logger.info(f"=== AGENTE EXECUTADO COM SUCESSO ===")

            # Validar estado final
            messages = final_state.get("messages", [])
            if not messages:
                logger.error(f"Estado final sem mensagens para thread_id {thread_id}")
                return MessageResponsePayload(
                    message="Desculpe, houve um problema interno. Tente novamente.",
                    phone_number=request_payload.phone_number,
                    message_id=request_payload.message_id,
                )

            logger.info(f"=== PROCESSANDO {len(messages)} MENSAGENS ===")
            for i, msg in enumerate(messages):
                logger.info(f"Msg {i+1}: {getattr(msg, 'type', 'unknown')} - {getattr(msg, 'content', 'sem conteúdo')[:50]}...")

            # Extrair resposta
            last_message = messages[-1]
            response_content = getattr(last_message, 'content', None)
            
            if not response_content:
                response_content = "Desculpe, houve um problema ao processar sua mensagem. Como posso ajudar?"

            logger.info(f"=== RESPOSTA EXTRAÍDA: {response_content[:100]}... ===")

            return MessageResponsePayload(
                message=response_content,
                phone_number=final_state.get("phone_number", request_payload.phone_number),
                message_id=final_state.get("message_id", request_payload.message_id),
            )

        except Exception as e:
            logger.error(f"=== ERRO CRÍTICO ===")
            logger.error(f"Erro: {str(e)}")
            logger.error(f"Tipo: {type(e).__name__}")
            logger.error(f"Traceback completo:")
            logger.error(traceback.format_exc())
            logger.error(f"=== FIM ERRO ===")
            raise