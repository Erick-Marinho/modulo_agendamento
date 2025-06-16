import logging

logger = logging.getLogger(__name__)

AGENT_TOOL_CALLER_NODE_NAME = "agent_tool_caller"
TOOL_NODE_NAME = "execute_medical_tools"


class MessageRouter:
    def route_orquestrator(self, state):
        """
        Função de decisão para roteamento condicional após o nó de orquestração.
        Lê o campo 'next_step' do estado E verifica conversation_context.
        """
        next_step = state.get("next_step", "").lower()
        conversation_context = (state.get("conversation_context") or "").lower()

        logger.info(
            f"Roteando (from route_orquestrator) com base no next_step: '{next_step}', conversation_context: '{conversation_context}'"
        )

        # 🆕 VERIFICAÇÃO DE CONTEXTO PRIMEIRO
        if conversation_context == "awaiting_date_selection":
            logger.info(
                "Usuário está escolhendo nova data. Direcionando para scheduling_info_node"
            )
            return "scheduling_info_node"

        # 🆕 VERIFICAÇÃO PARA UNCERTAINTY_HELP
        if conversation_context == "uncertainty_help":
            logger.info(
                "🎯 CONTEXTO UNCERTAINTY_HELP: Direcionando para agent_tool_caller"
            )
            return AGENT_TOOL_CALLER_NODE_NAME

        # Roteamento normal baseado em next_step (código existente)
        route_map = {
            "scheduling": "scheduling_node",
            "scheduling_info": "scheduling_info_node",
            "final_confirmation": "final_confirmation_node",
            "greeting": "greeting_node",
            "farewell": "farewell_node",
            "other": "other_node",
            "clarification": "clarification_node",
            "unclear": "clarification_node",
            "api_query": AGENT_TOOL_CALLER_NODE_NAME,
            "specialty_selection": AGENT_TOOL_CALLER_NODE_NAME,
            "api_interaction": AGENT_TOOL_CALLER_NODE_NAME,
            "uncertainty_help": AGENT_TOOL_CALLER_NODE_NAME,
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
        conversation_context = state.get("conversation_context", "")
        
        logger.info(
            f"Roteando (from decide_after_clarification) com base no next_step: '{next_step}', context: '{conversation_context}'"
        )

        # 🆕 SUPORTE PARA UNCERTAINTY_HELP: Redirecionar para agent_tool_caller
        if next_step == "agent_tool_caller":
            logger.info("🎯 CLARIFICATION REDIRECIONANDO: Para agent_tool_caller")
            return AGENT_TOOL_CALLER_NODE_NAME
        
        # 🆕 VERIFICAÇÃO DE CONTEXTO: Se é uncertainty_help, ir para agent_tool_caller  
        if conversation_context == "uncertainty_help":
            logger.info("🎯 CONTEXTO UNCERTAINTY_HELP: Redirecionando para agent_tool_caller")
            return AGENT_TOOL_CALLER_NODE_NAME

        if next_step == "END_AWAITING_USER":
            return "END_AWAITING_USER"
        elif next_step == "PROCEED_TO_VALIDATION":
            return "PROCEED_TO_VALIDATION"
        elif next_step == "check_availability_node":
            return "check_availability_node"
        elif next_step == "book_appointment_node":
            return "book_appointment_node"
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
        elif next_step == "book_appointment_node":
            return "book_appointment_node"
        elif next_step == "check_availability_node":
            return "check_availability_node"
        elif next_step == "validate_and_confirm":
            return "validate_and_confirm_node"
        else:
            logger.warning(
                f"Valor inesperado para next_step após check_completeness: {next_step}"
            )
            return "clarification_node"

    def route_after_check_availability(self, state):
        """
        Decide para onde ir depois do check_availability_node.
        """
        conversation_context = state.get("conversation_context", "").lower()
        next_step = state.get("next_step", "").lower()

        logger.info(
            f"Roteando após check_availability: next_step='{next_step}', context='{conversation_context}'"
        )

        # 🆕 Se já mostrou datas alternativas, finalizar
        if conversation_context == "awaiting_date_selection":
            logger.info("Check availability mostrou datas alternativas. Finalizando.")
            return "END"

        # 🔥 CORREÇÃO CRÍTICA: NÃO finalizar quando está awaiting_slot_selection
        # O fluxo deve continuar para aguardar a resposta do usuário
        if conversation_context == "awaiting_slot_selection":
            logger.info("Check availability encontrou horários. AGUARDANDO SELEÇÃO DO USUÁRIO.")
            return "END"  # ✅ Isso está correto - termina aqui para aguardar input do usuário

        # Fluxo padrão - ir para agent_tool_caller se necessário
        if next_step == "agent_tool_caller":
            logger.info("Check availability delegando para agent_tool_caller.")
            return "agent_tool_caller"

        logger.info("Check availability finalizando por padrão.")
        return "END"
