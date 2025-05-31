from langgraph.graph import StateGraph, END

from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.agents.node_functions.greeting_node import greeting_node
from langgraph.checkpoint.memory import MemorySaver

class MessageAgentBuilder:
    """
    Builder para criar o agente de mensagem
    """

    def __init__(self):
        """
        Inicializa e constroi o grafo do agente de mensagem
        """
        self.graph = StateGraph(MessageAgentState)

        self._build_graph()

        self._build_agent = self.graph.compile()

    def _build_graph(self):
        """
        Adiciona os nós e define as arestas para o workflow do agente.
        """
        self._build_node()
        self.graph.set_entry_point("greeting")
        self._build_edge()

    def _build_node(self):
        """
        Constroi o nó do agente de mensagem
        """
        self.graph.add_node("greeting", greeting_node)

    def _build_edge(self):
        """
        Constroi as arestas do agente de mensagem
        """
        self.graph.add_edge("greeting", END)

    def build_agent(self):
        """
        Constroi o agente de mensagem
        """
        return self._build_agent
    
    def build_memory_saver(self):
        """
        Constroi o MemorySaver
        """
        return MemorySaver()