import logging

logger = logging.getLogger(__name__)

AGENT_TOOL_CALLER_NODE_NAME = "agent_tool_caller"
TOOL_NODE_NAME = "execute_medical_tools"


class MessageRouter:
    def route_orquestrator(self, state):
        """
        Função de decisão para roteamento condicional após o nó de orquestração.
        Lê o campo 'next_step' do estado.
        """
        next_step = state.get("next_step", "").lower()

        logger.info(
            f"Roteando (from route_orquestrator) com base no next_step: '{next_step}'"
        )

        route_map = {
            "scheduling": "scheduling_node",
            "scheduling_info": "scheduling_info_node",
            "final_confirmation": "final_confirmation_node",
            "greeting": "greeting_node",
            "farewell": "farewell_node",
            "other": "other_node",
            AGENT_TOOL_CALLER_NODE_NAME.lower(): AGENT_TOOL_CALLER_NODE_NAME,
            "fallback_node": "fallback_node",
            "book_appointment_node": "book_appointment_node",
        }

        destination_node = route_map.get(next_step)

        if destination_node:
            logger.info(
                f"Roteador do orquestrador direcionando para: {destination_node}"
            )
            return destination_node
        else:
            logger.warning(
                f"Roteador do orquestrador: next_step '{next_step}' não mapeado. Direcionando para fallback_node."
            )
            return "fallback_node"

    def decide_after_tool_agent(self, state):
        """
        Decide para onde ir depois que o AGENT_TOOL_CALLER_NODE_NAME (agent_node_func) rodou.
        """
        next_step_from_agent = state.get("next_step", "").lower()
        logger.info(
            f"Roteando (from decide_after_tool_agent) com base no next_step_from_agent: '{next_step_from_agent}'"
        )

        if next_step_from_agent == TOOL_NODE_NAME.lower():
            logger.info(f"Direcionando para execução da ferramenta: {TOOL_NODE_NAME}")
            return TOOL_NODE_NAME

        # --- NOVA LÓGICA DE ROTEAMENTO ---
        if next_step_from_agent == "validate_and_confirm":
            logger.info(
                "Agente de ferramenta concluiu e está pronto para validar. Direcionando para validate_and_confirm_node."
            )
            return "validate_and_confirm_node"

        if next_step_from_agent == "completed":
            logger.info(
                "Agente de ferramenta respondeu diretamente. Finalizando fluxo do tool agent."
            )
            return "END"

        logger.warning(
            f"Fluxo inesperado após agente de ferramenta: next_step='{next_step_from_agent}'. Direcionando para fallback."
        )
        return "fallback_node"

    def decide_after_clarification(self, state):
        """
        Função de decisão para roteamento condicional após o nó de esclarecimento.
        Lê o campo 'next_step' do estado.
        """
        next_step = state.get("next_step")
        logger.info(
            f"Roteando (from decide_after_clarification) com base no next_step: '{next_step}'"
        )

        if next_step == "END_AWAITING_USER":
            return "END_AWAITING_USER"
        elif next_step == "PROCEED_TO_VALIDATION":
            return "PROCEED_TO_VALIDATION"
        else:
            logger.warning(
                f"Valor inesperado para next_step após clarification_node: {next_step}. Direcionando para DEFAULT_END"
            )
            return "DEFAULT_END"

    def route_after_completeness_check(self, state):
        """
        Função de decisão após verificar completude dos dados.
        """
        next_step = state.get("next_step")
        logger.info(
            f"Roteando (from route_after_completeness_check) com base no next_step: '{next_step}'"
        )

        if next_step == "clarification":
            return "clarification_node"
        elif next_step == "validate_and_confirm":
            return "validate_and_confirm_node"
        else:
            logger.warning(
                f"Valor inesperado para next_step após check_completeness: {next_step}"
            )
            return "clarification_node"
