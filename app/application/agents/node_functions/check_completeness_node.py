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

    missing_fields = _get_missing_essential_fields(extracted_details)

    if missing_fields:
        logger.info(f"Campos essenciais faltando: {missing_fields}")
        return {
            **state,
            "next_step": "clarification",
            "missing_fields": missing_fields,
        }
    else:
        logger.info("Todos os campos essenciais estão presentes")
        return {**state, "next_step": "check_availability_node", "missing_fields": []}


def _get_missing_essential_fields(details) -> List[str]:
    """
    Identifica quais campos essenciais estão faltando.
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

    return missing_fields
