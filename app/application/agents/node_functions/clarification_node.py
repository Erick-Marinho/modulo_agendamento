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
            
            # 🔧 CORREÇÃO SIMPLES: Se usuário está incerto sobre especialidade, sempre ajudar
            missing_fields_safe = missing_fields or []
            
            # Se está perguntando sobre especialidade/profissional OU se não tem missing_fields
            should_show_specialties = (
                not missing_fields_safe or  # Sem campos específicos
                any("especialidade" in field.lower() for field in missing_fields_safe) or  # Contém "especialidade"
                any("profissional" in field.lower() for field in missing_fields_safe)  # Contém "profissional"
            )
            
            logger.info(f"🔍 DEBUG: missing_fields = {missing_fields_safe}")
            logger.info(f"🔍 DEBUG: should_show_specialties = {should_show_specialties}")
            
            if should_show_specialties:
                logger.info("✅ REDIRECIONANDO: Para agent_tool_caller com contexto uncertainty_help")
                return {
                    **state,
                    "next_step": "agent_tool_caller",
                    "conversation_context": "uncertainty_help",
                }

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

    # 🆕 PRIORIZAR UM CAMPO POR VEZ: Usar apenas o próximo campo mais importante
    if missing_fields:
        # Se há campos missing fornecidos pelo estado, usar apenas o primeiro (mais prioritário)
        priority_field = missing_fields[0] if missing_fields else None
        logger.info(f"Campo prioritário a ser perguntado: {priority_field}")
    else:
        # Se não há missing_fields no estado, calcular o próximo campo prioritário
        priority_field = _get_next_priority_field(details)
        logger.info(f"Campo prioritário calculado: {priority_field}")

    if priority_field:
        logger.info(f"Informação de agendamento faltante: {priority_field}")

        service_type_info = (
            details.service_type if details.service_type else "serviço desejado"
        )

        llm_service: ILLMService = LLMFactory.create_llm_service("openai")

        try:
            ai_response_text = llm_service.generate_clarification_question(
                service_type=service_type_info,
                missing_fields_list=priority_field,
                professional_name=details.professional_name,
                specialty=details.specialty,
                date_preference=details.date_preference,
                time_preference=details.time_preference,
                patient_name=details.patient_name,
            )
            logger.info(f"Pergunta de esclarecimento gerada: {ai_response_text}")
        except Exception as e:
            logger.error(f"Erro ao gerar pergunta de esclarecimento via LLM: {e}")
            ai_response_text = None

        # 🆕 TRATAMENTO CRÍTICO: Garantir que ai_response_text nunca seja None
        if not ai_response_text:
            logger.warning("LLM retornou None - usando fallback manual")
            ai_response_text = _generate_fallback_question(priority_field, details)

        current_messages.append(AIMessage(content=ai_response_text))
        return {
            **state,
            "messages": current_messages,
            "next_step": "END_AWAITING_USER",
            "conversation_context": "scheduling_flow",
        }
    else:
        logger.info(
            "Todos os detalhes essenciais para o agendamento foram coletados e estão presentes."
        )
        return {**state, "next_step": "check_availability_node"}


def _get_next_priority_field(details: SchedulingDetails) -> Optional[str]:
    """
    Retorna o próximo campo essencial mais prioritário que está faltando.
    Implementa ordem de prioridade para evitar perguntas múltiplas.
    """
    # PRIORIDADE 1: Especialidade ou profissional
    if not details.specialty and not details.professional_name:
        return "especialidade ou nome do profissional"
    
    # PRIORIDADE 2: Data de preferência
    if not details.date_preference:
        return "data de preferência"
    
    # PRIORIDADE 3: Turno/Horário de preferência
    if not details.time_preference:
        # Se date_preference indica "proximidade", perguntar sobre TURNO
        if details.date_preference and any(
            phrase in details.date_preference.lower()
            for phrase in ["mais próxima", "mais proxima", "primeira disponível", "quanto antes"]
        ):
            logger.info(f"🎯 Data indica proximidade ('{details.date_preference}') - perguntando sobre TURNO")
            return "turno de preferência"
        else:
            logger.info(f"🎯 Data específica ('{details.date_preference}') - perguntando sobre HORÁRIO")
            return "horário de preferência"
    
    # PRIORIDADE 4: Nome do paciente (só pergunta por último)
    if not details.patient_name:
        return "nome do paciente"
    
    # Se chegou aqui, todos os campos essenciais estão preenchidos
    return None


def _generate_fallback_question(field: str, details: SchedulingDetails) -> str:
    """
    Gera pergunta manual como fallback quando LLM falha.
    """
    if field == "especialidade ou nome do profissional":
        return "Qual especialidade médica você procura?"
    elif field == "data de preferência":
        return "Para qual data você gostaria de agendar?"
    elif field == "turno de preferência":
        professional_name = details.professional_name or "o profissional"
        return f"Qual turno você prefere para a consulta com {professional_name}? (manhã ou tarde)"
    elif field == "horário de preferência":
        return "Qual horário você gostaria de agendar?"
    elif field == "nome do paciente":
        return "Qual é o nome do paciente para o agendamento?"
    else:
        return f"Para continuarmos com o agendamento, preciso saber: {field}. Pode me informar?"
