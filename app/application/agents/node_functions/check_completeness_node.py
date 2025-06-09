from app.application.agents.state.message_agent_state import MessageAgentState
from typing import List
import logging

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
        return {**state, "next_step": "clarification", "missing_fields": missing_fields}
    else:
        logger.info("Todos os campos essenciais estão presentes")
        return {**state, "next_step": "validate_and_confirm"}


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
        missing_fields.append("horário de preferência")

    if not details.service_type:
        missing_fields.append("tipo de serviço")

    return missing_fields
