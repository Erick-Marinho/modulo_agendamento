import logging
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage

from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.interfaces.illm_service import ILLMService
from app.domain.sheduling_details import SchedulingDetails
from app.infrastructure.services.llm.llm_factory import LLMFactory

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


def _detect_uncertainty_simple(user_message: str) -> bool:
    """
    Detecção simples de incerteza por enquanto para debug.
    """
    uncertainty_phrases = [
        "não sei", "nao sei", "naõ sei",
        "não tenho certeza", "nao tenho certeza", 
        "qualquer um", "tanto faz", "qualquer",
        "não conheço", "nao conheço", "não conheco",
        "você decide", "voce decide",
        "o que você recomenda", "o que voce recomenda"
    ]
    
    user_lower = user_message.lower().strip()
    return any(phrase in user_lower for phrase in uncertainty_phrases)


def clarification_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó responsável por gerar uma pergunta de esclarecimento para o usuário.
    """
    logger.info("--- EXECUTANDO NÓ DE ESCLARECIMENTO ---")

    current_messages: List[HumanMessage | AIMessage] = state.get("messages", [])
    details: Optional[SchedulingDetails] = state.get("extracted_scheduling_details")
    missing_fields = state.get("missing_fields", [])

    # 🧠 DETECÇÃO DE INCERTEZA: Versão simples para test
    if current_messages:
        # Pegar a última mensagem do usuário
        last_user_message = ""
        for msg in reversed(current_messages):
            if hasattr(msg, 'content') and 'Human' in str(type(msg)):
                last_user_message = msg.content
                break
        
        logger.info(f"🔍 DEBUG: Última mensagem do usuário: '{last_user_message}'")
        
        if last_user_message and _detect_uncertainty_simple(last_user_message):
            logger.info("🎯 DETECTADA INCERTEZA SIMPLES: Redirecionando para especialidades")
            
            # Verificar se falta especialidade ou profissional
            needs_specialty_info = any(
                field in ["nome do profissional", "especialidade", "nome do profissional ou especialidade"] 
                for field in missing_fields
            )
            
            logger.info(f"🔍 DEBUG: missing_fields = {missing_fields}")
            logger.info(f"🔍 DEBUG: needs_specialty_info = {needs_specialty_info}")
            
            if needs_specialty_info:
                logger.info("✅ REDIRECIONANDO: Para agent_tool_caller com contexto uncertainty_help")
                return {
                    **state,
                    "next_step": "agent_tool_caller",
                    "conversation_context": "uncertainty_help",
                }
            else:
                logger.info("❌ NÃO REDIRECIONOU: needs_specialty_info é False")

    if details is None:
        logger.warning(
            "Detalhes do agendamento não encontrados no estado para esclarecimento."
        )
        ai_response_text = "Humm, não consegui entender todos os detalhes para o seu agendamento. Poderia me dizer o nome do profissional, a data e o horário que você gostaria, por favor?"
        current_messages.append(AIMessage(content=ai_response_text))
        return {
            **state,
            "messages": current_messages,
            "next_step": "END_AWAITING_USER",
        }

    # Usar missing_fields do estado se disponível, senão calcular
    if not missing_fields:
        missing_fields = []
        if not details.professional_name:
            missing_fields.append("nome do profissional")
        if not details.date_preference:
            missing_fields.append("data de preferência")
        if not details.time_preference:
            missing_fields.append("turno de preferência (manhã ou tarde)")
        if not details.specialty:
            missing_fields.append("especialidade")

    if missing_fields:
        logger.info(f"Informações de agendamento faltantes: {missing_fields}")

        service_type_info = (
            details.service_type if details.service_type else "serviço desejado"
        )
        missing_fields_str = _format_missing_fields_for_prompt(missing_fields)

        llm_service: ILLMService = LLMFactory.create_llm_service("openai")

        try:
            ai_response_text = llm_service.generate_clarification_question(
                service_type=service_type_info,
                missing_fields_list=missing_fields_str,
                professional_name=details.professional_name,
                specialty=details.specialty,
                date_preference=details.date_preference,
                time_preference=details.time_preference,
            )
            logger.info(f"Pergunta de esclarecimento gerada: {ai_response_text}")
        except Exception as e:
            logger.error(f"Erro ao gerar pergunta de esclarecimento via LLM: {e}")
            ai_response_text = f"Para continuarmos com o agendamento do(a) {service_type_info}, preciso de mais alguns detalhes: {missing_fields_str}. Poderia me informar, por favor?"

        current_messages.append(AIMessage(content=ai_response_text))
        return {
            **state,
            "messages": current_messages,
            "next_step": "END_AWAITING_USER",
        }
    else:
        logger.info(
            "Todos os detalhes essenciais para o agendamento foram coletados e estão presentes."
        )
        return {**state, "next_step": "check_availability_node"}
