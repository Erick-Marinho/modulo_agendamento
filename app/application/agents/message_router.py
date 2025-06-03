import logging

logger = logging.getLogger(__name__)

class MessageRouter:
   def route_orquestrator(self, state):
        """
        Função de decisão para roteamento condicional após o nó de orquestração.
        Lê o campo 'next_step' do estado.
        """
        next_step = state.get("next_step").lower()

        if "scheduling" in next_step:
            return "scheduling"
        elif "greeting" in next_step:
            return "greeting"
        elif "farewell" in next_step:
            return "farewell"
        else:
            return "fallback_node"

   def decide_after_clarification(self, state):
    """
    Função de decisão para roteamento condicional após o nó de esclarecimento.
    Lê o campo 'next_step' do estado.
    """

    next_step = state.get("next_step")
    if next_step == "END_AWAITING_USER":
        return "END_AWAITING_USER"
    elif next_step == "PROCEED_TO_VALIDATION":
        return "PROCEED_TO_VALIDATION"
    else:
        logger.warning(f"valor inesperado para next_step após clarification_node: {next_step}. Direcionando para END")
        return "DEFAULT_END"
