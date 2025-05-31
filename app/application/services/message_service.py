import logging

from langchain_core.messages import HumanMessage

from app.application.agents.message_agent_builder import MessageAgentBuilder
from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.dto.message_request_dto import MessageRequestPayload
from app.application.dto.message_response_dto import MessageResponsePayload

logger = logging.getLogger(__name__)

class MessageService:
    """
    Serviço para processar a mensagem recebida
    """

    def __init__(self):
        pass

    async def process_message(self, request_payload: MessageRequestPayload) -> MessageResponsePayload:
        """
        Processa a mensagem recebida

        Args:
            message: MessageRequestPayload

        Returns:
            MessageResponsePayload
        """
        logger.info(f"Processando mensagem: {request_payload}")

        message_agent_builder = MessageAgentBuilder()

        message_agent = message_agent_builder.build_agent()

        initial_state: MessageAgentState = {
            "message": request_payload.message,
            "phone_number": request_payload.phone_number,
            "message_id": request_payload.message_id,
            "messages": [HumanMessage(content=request_payload.message)]
        }

        final_state: MessageAgentState = message_agent.invoke(initial_state)

        logger.info(f"Mensagem processada: {final_state}")

        return MessageResponsePayload(
            message=final_state["message"],
            phone_number=final_state["phone_number"],
            message_id=final_state["message_id"],
            messages=final_state["messages"]
        )
