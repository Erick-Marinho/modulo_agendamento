import logging
from typing import List

from app.application.agents.state.message_agent_state import MessageAgentState

logger = logging.getLogger(__name__)


def check_completeness_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó que verifica se temos informações suficientes para prosseguir com o agendamento.
    """
    logger.info("--- Verificando completude dos dados de agendamento ---")

    extracted_details = state.get("extracted_scheduling_details")

    if not extracted_details:
        logger.warning("Nenhum detalhe extraído encontrado")
        return {**state, "next_step": "clarification"}

    # 🆕 NOVA LÓGICA: Priorizar um campo por vez
    missing_field = _get_next_missing_essential_field(extracted_details)

    if missing_field:
        logger.info(f"Próximo campo essencial faltando: {missing_field}")
        return {
            **state,
            "next_step": "clarification",
            "missing_fields": [missing_field],  # 🔧 Apenas UM campo por vez
        }
    else:
        logger.info("Todos os campos essenciais estão presentes")
        return {**state, "next_step": "check_availability_node", "missing_fields": []}


def _get_next_missing_essential_field(details) -> str:
    """
    Retorna o PRÓXIMO campo essencial mais prioritário que está faltando.
    Implementa ordem de prioridade para evitar perguntas múltiplas simultâneas.
    """
    # PRIORIDADE 1: Especialidade ou profissional
    if not details.specialty and not details.professional_name:
        return "especialidade ou nome do profissional"
    
    # PRIORIDADE 2: Data de preferência
    if not details.date_preference:
        return "data de preferência"
    
    # PRIORIDADE 3: Turno/Horário de preferência
    if not details.time_preference:
        # 🔧 NOVA LÓGICA: Se date_preference indica "proximidade", perguntar sobre TURNO
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


def _get_missing_essential_fields(details) -> List[str]:
    """
    DEPRECATED: Função mantida por compatibilidade, mas não deve ser usada.
    Use _get_next_missing_essential_field() para evitar perguntas duplas.
    """
    missing_fields = []

    if not details.specialty and not details.professional_name:
        missing_fields.append("especialidade ou nome do profissional")

    if not details.date_preference:
        missing_fields.append("data de preferência")

    if not details.time_preference:
        # 🔧 NOVA LÓGICA: Se date_preference indica "proximidade", perguntar sobre TURNO
        if details.date_preference and any(
            phrase in details.date_preference.lower()
            for phrase in ["mais próxima", "mais proxima", "primeira disponível", "quanto antes"]
        ):
            missing_fields.append("turno de preferência")
            logger.info(f"🎯 Data indica proximidade ('{details.date_preference}') - perguntando sobre TURNO")
        else:
            missing_fields.append("horário de preferência")
            logger.info(f"🎯 Data específica ('{details.date_preference}') - perguntando sobre HORÁRIO")

    # 🆕 ADICIONADO: Validação do nome do paciente
    if not details.patient_name:
        missing_fields.append("nome do paciente")

    return missing_fields
