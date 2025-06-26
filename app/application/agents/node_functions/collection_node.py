from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from app.domain.sheduling_details import SchedulingDetails
from typing import Optional, List
from langchain_core.messages import BaseMessage, HumanMessage
import logging

logger = logging.getLogger(__name__)


def _format_conversation_history_for_prompt(
    messages: List[BaseMessage], max_messages: int = 8
) -> str:
    if not messages:
        return "Nenhuma conversa ainda"

    recent_messages = messages[-max_messages:]

    formatted_history = []

    for msg in recent_messages:
        role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
        formatted_history.append(f"{role}: {msg.content}")

    return "\n".join(formatted_history)


def _merge_scheduling_details(
    existing: Optional[SchedulingDetails], new: Optional[SchedulingDetails]
) -> Optional[SchedulingDetails]:
    """Mescla detalhes de agendamento, preservando dados existentes."""
    if not existing:
        return new
    if not new:
        return existing

    return SchedulingDetails(
        professional_name=new.professional_name or existing.professional_name,
        specialty=new.specialty or existing.specialty,
        date_preference=new.date_preference or existing.date_preference,
        time_preference=new.time_preference or existing.time_preference,
        specific_time=new.specific_time or existing.specific_time,
        service_type=new.service_type or existing.service_type or "consulta",
        patient_name=new.patient_name or existing.patient_name,
    )


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

    existing_details = state.get("extracted_scheduling_details")
    
    conversation_hitory_str = _format_conversation_history_for_prompt(
        all_messages, max_messages=8
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

        final_details = _merge_scheduling_details(existing_details, extracted_data)

        logger.info(f"Detalhes do agendamento extraídos: {extracted_data}")
        logger.info(f"Detalhes finais mesclados: {final_details}")

        return {**state, "extracted_scheduling_details": final_details}
    except Exception as e:
        logger.error(f"Erro ao extrair os detalhes do agendamento: {e}")
        return {**state, "extracted_scheduling_details": existing_details}
