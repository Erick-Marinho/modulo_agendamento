import logging

from app.application.agents.state.message_agent_state import MessageAgentState

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
        next_step = state.get("next_step")

        if not next_step:
            return "DEFAULT_END"
        
        return next_step

    def route_validation_scheduling_data(self, state: MessageAgentState):
        next_step = state.get("next_step")

        if not next_step:
            return "DEFAULT_END"

        return next_step
        
    def route_after_scheduling_node(self, state: MessageAgentState) -> str:
        next_step = state.get("next_step")
        
        if not next_step:
            return "DEFAULT_END"
        
        return next_step
    
    def route_after_update_and_clarify_node(self, state: MessageAgentState) -> str:
        next_step = state.get("next_step")

        if not next_step:
            return "DEFAULT_END"
        
        return next_step