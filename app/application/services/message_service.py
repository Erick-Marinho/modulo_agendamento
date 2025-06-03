import logging

from fastapi import Depends
from langchain_core.messages import HumanMessage
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

    def __init__(self, checkpointer: SaveCheckpointInterface = Depends(MongoDBSaverCheckpointer)):
        """
        Inicializa o serviço de mensagem

        Args:
            checkpointer: SaveCheckpointInterface (MongoDBSaver oficial por padrão)
        """
        self.checkpointer = checkpointer
        self.message_agent_builder = MessageAgentBuilder(checkpointer=checkpointer.create_checkpoint())
        self.message_agent = self.message_agent_builder.build_agent()
        logger.info("MessageService inicializado com MongoDBSaver LangGraph")

    async def process_message(self, request_payload: MessageRequestPayload) -> MessageResponsePayload:
        """
        Processa a mensagem recebida

        Args:
            message: MessageRequestPayload

        Returns:
            MessageResponsePayload
        """
        logger.info(f"Processando mensagem: {request_payload}")

        thread_id = request_payload.phone_number
        config = {"configurable": {"thread_id": thread_id}}

        initial_state: MessageAgentState = {
            "message": request_payload.message,
            "phone_number": request_payload.phone_number,
            "message_id": request_payload.message_id,
            "messages": [HumanMessage(content=request_payload.message)]
        }

        try:
            final_state: MessageAgentState = self.message_agent.invoke(initial_state, config=config)

            if final_state and final_state.get("messages"):
                logger.info(f"Histórico de mensagens no estado final para thread_id {thread_id}:")

                for i, msg in enumerate(final_state["messages"]):
                    logger.info(f"  Msg {i+1}: Type='{msg.type}', Content='{msg.content}'")

            else:
                logger.warning(f"Nenhuma mensagem no estado final para thread_id {thread_id}.")

            logger.info(f"Mensagem processada com sucesso para thread_id: {thread_id}")

            return MessageResponsePayload(
                message=final_state.get("messages")[-1].content,
                phone_number=final_state.get("phone_number", request_payload.phone_number),
                message_id=final_state.get("message_id", request_payload.message_id),
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem para thread_id {thread_id}: {e}")
            raise