from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from app.domain.sheduling_details import SchedulingDetails
from typing import Optional, List
from langchain_core.messages import BaseMessage, HumanMessage
import logging

logger = logging.getLogger(__name__)


def _format_conversation_history_for_prompt(
    messages: List[BaseMessage], max_messages: int = 5
) -> str:
    if not messages:
        return "Nenhuma conversa ainda"

    recent_messages = messages[-max_messages:]

    formatted_history = []

    for msg in recent_messages:
        role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
        formatted_history.append(f"{role}: {msg.content}")

    return "\n".join(formatted_history)


def collection_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó responsável por coletar os detalhes do agendamento da mensagem do usuário,
    utilizando o ILLMService.
    """

    logger.info("Iniciando coleta de detalhes do agendamento")
    all_messages: List[BaseMessage] = state.get("messages", [])

    if not all_messages:
        logger.error(
            "Não foi possível coletar os detalhes do agendamento. Mensagem do usuário não encontrada."
        )
        return {**state, "extracted_scheduling_details": None}

    conversation_hitory_str = _format_conversation_history_for_prompt(
        all_messages, max_messages=5
    )
    logger.info(
        f"Histórico formatado para extração:\n{conversation_hitory_str}"
    )

    try:
        llm_type = "openai"
        llm_service = LLMFactory.create_llm_service(llm_type)

        extracted_data = llm_service.extract_scheduling_details(
            user_message=conversation_hitory_str
        )

        logger.info(f"Detalhes do agendamento extraídos: {extracted_data}")

        return {**state, "extracted_scheduling_details": extracted_data}
    except Exception as e:
        logger.error(f"Erro ao extrair os detalhes do agendamento: {e}")
        return {**state, "extracted_scheduling_details": None}
