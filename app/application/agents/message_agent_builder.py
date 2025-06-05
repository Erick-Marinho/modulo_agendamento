from langgraph.graph import StateGraph, END

from app.application.agents.message_router import MessageRouter
from app.application.agents.node_functions.fallback_node import fallback_node
from app.application.agents.node_functions.scheduling_node import scheduling_node
from app.application.agents.node_functions.orquestrator_node import orquestrator_node
from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.agents.node_functions.greeting_node import greeting_node
from langgraph.checkpoint.base import BaseCheckpointSaver
from app.application.agents.node_functions.farewell_node import farewell_node
from app.application.agents.node_functions.collection_node import collection_node
from app.application.agents.node_functions.clarification_node import clarification_node
from app.infrastructure.persistence.mongodb_saver_checkpointer import MongoDBSaverCheckpointer
from app.application.agents.node_functions.scheduling_info_node import scheduling_info_node
from app.application.agents.node_functions.check_completeness_node import check_completeness_node
from app.application.agents.node_functions.other_node import other_node
from app.application.agents.node_functions.validate_and_confirm_node import validate_and_confirm_node
from app.application.agents.node_functions.final_confirmation_node import final_confirmation_node

class MessageAgentBuilder:
    """
    Builder para criar o agente de mensagem
    """

    def __init__(self, checkpointer: BaseCheckpointSaver):
        """
        Inicializa e constroi o grafo do agente de mensagem
        """
        self.graph = StateGraph(MessageAgentState)
        self.route_orquestrator = MessageRouter().route_orquestrator
        self.route_after_clarification = MessageRouter().decide_after_clarification
        # inserção
        self.route_after_completeness_check = MessageRouter().route_after_completeness_check
        self._build_graph()

        self._build_agent = self.graph.compile(checkpointer=checkpointer)

    def _build_graph(self):
        """
        Adiciona os nós e define as arestas para o workflow do agente.
        """
        self._build_node()
        self.graph.set_entry_point("orquestrator_node")
        self._build_edge()

    def _build_node(self):
        """
        Constroi o nó do agente de mensagem
        """
        self.graph.add_node("orquestrator_node", orquestrator_node)
        self.graph.add_node("greeting_node", greeting_node)
        self.graph.add_node("scheduling_node", scheduling_node)
        self.graph.add_node("scheduling_info_node", scheduling_info_node)
        self.graph.add_node("collection_node", collection_node)
        self.graph.add_node("clarification_node", clarification_node)
        self.graph.add_node("check_completeness_node", check_completeness_node)
        self.graph.add_node("validate_and_confirm_node", validate_and_confirm_node)
        self.graph.add_node("final_confirmation_node", final_confirmation_node)
        self.graph.add_node("other_node", other_node)
        self.graph.add_node("farewell_node", farewell_node)
        self.graph.add_node("fallback_node", fallback_node)

    def _build_edge(self):
        """
        Constroi as arestas do agente de mensagem
        """
        # Roteamento inicial do orquestrador
        self.graph.add_conditional_edges(
            "orquestrator_node",
            self.route_orquestrator,
            {
                "scheduling": "scheduling_node",
                "scheduling_info": "scheduling_info_node",
                "final_confirmation": "final_confirmation_node",
                "greeting": "greeting_node",
                "farewell": "farewell_node",
                "other": "other_node",
                "fallback_node": "fallback_node",
            }
        )

        # Fluxo do agendamento inicial
        self.graph.add_edge("scheduling_node", "collection_node")
        self.graph.add_edge("collection_node", "clarification_node")

        # Fluxo quando recebemos informações de agendamento
        self.graph.add_conditional_edges(
            "scheduling_info_node",
            lambda state: state.get("next_step", "clarification"),
            {
                "check_completeness": "check_completeness_node",
                "clarification": "clarification_node"
            }
        )

        # Fluxo após verificar completude
        self.graph.add_conditional_edges(
            "check_completeness_node",
            lambda state: state.get("next_step", "clarification"),
            {
                "clarification": "clarification_node",
                "validate_and_confirm": "validate_and_confirm_node" 
            }
        )

        # Fluxo após validação e confirmação
        self.graph.add_conditional_edges(
            "validate_and_confirm_node",
            lambda state: state.get("next_step", "clarification"),
            {
                "awaiting_final_confirmation": END,
                "clarification": "clarification_node"
            }
        )

        # Quando o usuário responde à confirmação final
        # Este será ativado quando o orquestrador detectar que estamos esperando confirmação
        self.graph.add_conditional_edges(
            "final_confirmation_node",
            lambda state: state.get("next_step", "completed"),
            {
                "appointment_confirmed": END,
                "awaiting_correction": END,
                "awaiting_final_confirmation": END,
                "completed": END
            }
        )

        # Fluxo do esclarecimento
        self.graph.add_conditional_edges(
            "clarification_node",
            self.route_after_clarification,
            {
                "END_AWAITING_USER": END,
                "PROCEED_TO_VALIDATION": END,
                "DEFAULT_END": END,
            }
        )

        self.graph.add_edge("greeting_node", END)
        self.graph.add_edge("other_node", END)
        self.graph.add_edge("fallback_node", END)
        self.graph.add_edge("farewell_node", END)

    def build_agent(self):
        """
        Constroi o agente de mensagem
        """
        print(self._build_agent.get_graph().draw_mermaid())
        
        return self._build_agent
    
async def get_message_agent():
    mongodb_provider = MongoDBSaverCheckpointer()
    
    actual_mongo_checkpointer = mongodb_provider.create_checkpoint()

    builder = MessageAgentBuilder(checkpointer=actual_mongo_checkpointer)

    agent = builder.build_agent()

    return agent
    