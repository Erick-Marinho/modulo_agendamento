import logging

logger = logging.getLogger(__name__)

class MessageRouter:
    def route_orquestrator(self, state):
        """
        Função de decisão para roteamento condicional após o nó de orquestração.
        Lê o campo 'next_step' do estado.
        """
        next_step = state.get("next_step", "").lower()
        
        logger.info(f"Roteando com base no next_step: '{next_step}'")

        if next_step == "scheduling":
            return "scheduling"
        elif next_step == "scheduling_info":
            return "scheduling_info"
        elif next_step == "greeting":
            return "greeting"
        elif next_step == "farewell":
            return "farewell"
        elif next_step == "other":
            return "other"
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
            logger.warning(f"Valor inesperado para next_step após clarification_node: {next_step}. Direcionando para END")
            return "DEFAULT_END"
    
    def route_after_completeness_check(self, state):
        """
        Função de decisão após verificar completude dos dados.
        """
        next_step = state.get("next_step")
        
        if next_step == "clarification":
            return "clarification"
        elif next_step == "validate_and_confirm":
            return "validate_and_confirm"
        else:
            logger.warning(f"Valor inesperado para next_step após check_completeness: {next_step}")
            return "clarification"