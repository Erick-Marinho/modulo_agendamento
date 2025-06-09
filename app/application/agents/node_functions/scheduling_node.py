import logging
from app.application.agents.state.message_agent_state import MessageAgentState

logger = logging.getLogger(__name__)


def scheduling_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó que inicia o fluxo de agendamento.
    Prepara para a coleta de informações e passa o estado adiante.
    """
    logger.info("Iniciando fluxo de agendamento")

    return state
