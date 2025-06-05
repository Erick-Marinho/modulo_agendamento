from app.application.agents.state.message_agent_state import MessageAgentState
from app.domain.sheduling_details import SchedulingDetails
from app.infrastructure.services.llm.llm_factory import LLMFactory
from app.application.interfaces.illm_service import ILLMService 
from langchain_core.messages import AIMessage, HumanMessage

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

def _format_missing_fields_for_prompt(missing_fields: List[str]) -> str:
    """Helper para formatar a lista de campos faltantes para o prompt."""
    if not missing_fields:
        return ""
    if len(missing_fields) == 1:
        return missing_fields[0]
    if len(missing_fields) == 2:
        return " e ".join(missing_fields)
    return ", ".join(missing_fields[:-1]) + ", e " + missing_fields[-1]

def clarification_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó responsável por gerar uma pergunta de esclarecimento para o usuário.
    Se a extração falhou completamente, pedir de forma genérica.
    Se a extração foi parcial, gerar uma pergunta para o usuário solicitando informações faltantes.
    Se a extração foi completa, não gerar pergunta.
    Se a extração foi completa, mas faltam informações essenciais, gerar uma pergunta para o usuário solicitando informações faltantes.
    Se a extração foi completa, mas faltam informações essenciais, gerar uma pergunta para o usuário solicitando informações faltantes.
    """
    logger.info("--- EXECUTANDO NÓ DE ESCLARECIMENTO ---")
    
    current_messages: List[HumanMessage | AIMessage] = state.get("messages", [])
    details: Optional[SchedulingDetails] = state.get("extracted_scheduling_details")

    if details is None:
        logger.warning("Detalhes do agendamento não encontrados no estado para esclarecimento. Solicitando informações básicas.")
        ai_response_text = "Humm, não consegui entender todos os detalhes para o seu agendamento. Poderia me dizer o nome do profissional, a data e o horário que você gostaria, por favor?"
        current_messages.append(AIMessage(content=ai_response_text))
        return {**state, "messages": current_messages, "next_step": "END_AWAITING_USER"}

    missing_fields: List[str] = []
    if not details.professional_name:
        missing_fields.append("nome do profissional")
    if not details.date_preference:
        missing_fields.append("data de preferência")
    if not details.time_preference:
        missing_fields.append("turno de preferência (manhã ou tarde)")
    if not details.service_type:
        missing_fields.append("tipo de serviço")
    if not details.specialty:
        missing_fields.append("especialidade")

    if missing_fields:
        logger.info(f"Informações de agendamento faltantes: {missing_fields}")
        
        service_type_info = details.service_type if details.service_type else "serviço desejado"
        missing_fields_str = _format_missing_fields_for_prompt(missing_fields)
        
        llm_service: ILLMService = LLMFactory.create_llm_service("openai") 

        try:
            ai_response_text = llm_service.generate_clarification_question(
                service_type=service_type_info,
                missing_fields_list=missing_fields_str,
                professional_name=details.professional_name,
                specialty=details.specialty,
                date_preference=details.date_preference,
                time_preference=details.time_preference
            )
            logger.info(f"Pergunta de esclarecimento gerada: {ai_response_text}")
        except Exception as e:
            logger.error(f"Erro ao gerar pergunta de esclarecimento via LLM: {e}")
            ai_response_text = f"Para continuarmos com o agendamento do(a) {service_type_info}, preciso de mais alguns detalhes: {missing_fields_str}. Poderia me informar, por favor?"

        current_messages.append(AIMessage(content=ai_response_text))
        return {**state, "messages": current_messages, "next_step": "END_AWAITING_USER"}
    else:
        logger.info("Todos os detalhes essenciais para o agendamento foram coletados e estão presentes.")
        return {**state, "next_step": "PROCEED_TO_VALIDATION"}