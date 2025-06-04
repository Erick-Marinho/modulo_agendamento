from langgraph.graph import StateGraph, END

from app.application.agents.message_router import MessageRouter
from app.application.agents.node_functions.validation_scheduling_data_node import validation_scheduling_data_node
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

class MessageAgentBuilder:
    """
    Builder para criar o agente de mensagem
    """

    def __init__(self, checkpointer: BaseCheckpointSaver):
        """
        Inicializa e constroi o grafo do agente de mensagem
        """
        self.routers = MessageRouter()
        self.graph = StateGraph(MessageAgentState)
        self.route_orquestrator = self.routers.route_orquestrator
        self.route_after_clarification = self.routers.decide_after_clarification
        self.route_validation_scheduling_data = self.routers.route_validation_scheduling_data
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
        self.graph.add_node("collection_node", collection_node)
        self.graph.add_node("clarification_node", clarification_node)
        self.graph.add_node("validation_scheduling_data_node", validation_scheduling_data_node)
        self.graph.add_node("farewell_node", farewell_node)
        self.graph.add_node("fallback_node", fallback_node)

    def _build_edge(self):
        """
        Constroi as arestas do agente de mensagem
        """
        self.graph.add_conditional_edges(
            "orquestrator_node",
            self.route_orquestrator,
            {
                "scheduling": "scheduling_node",
                "greeting": "greeting_node",
                "farewell": "farewell_node",
                "fallback_node": "fallback_node"
            }
        )
        self.graph.add_edge("scheduling_node", "collection_node")
        self.graph.add_edge("collection_node", "clarification_node")
        

        self.graph.add_conditional_edges(
            "clarification_node",
            self.route_after_clarification,
            {
                "END_AWAITING_USER": END,
                "PROCEED_TO_VALIDATION": "validation_scheduling_data_node",
                "DEFAULT_END": END,
            }
        )

        self.graph.add_conditional_edges(
            "validation_scheduling_data_node",
            self.route_validation_scheduling_data,
            {
                "END_AWAITING_USER_VALIDATION": END,
                "CONFIRMED_SCHEDULING_DATA": END, # proximo node
                "ALTER_SCHEDULING_DATA": "collection_node",
                "UNCLEAR": END,
                "DEFAULT_END": END,
            }
        )

        self.graph.add_edge("greeting_node", END)
        self.graph.add_edge("fallback_node", END)
        self.graph.add_edge("farewell_node", END)

    def build_agent(self):
        """
        Constroi o agente de mensagem
        """
        print(self._build_agent.get_graph().draw_mermaid())
        
        return self._build_agent
    
def get_message_agent():
    mongodb_provider = MongoDBSaverCheckpointer()
    actual_mongo_checkpointer = mongodb_provider.create_checkpoint()

    builder = MessageAgentBuilder(checkpointer=actual_mongo_checkpointer)

    agent = builder.build_agent()

    return agent
    