# app/application/agents/message_agent_builder.py
from langgraph.checkpoint.base import BaseCheckpointSaver  # Para o tipo do checkpointer
from langgraph.graph import END, StateGraph

from app.application.agents.message_router import MessageRouter
from app.application.agents.node_functions.api_tools_node import (
    TOOL_NODE_NAME as EXECUTE_MEDICAL_TOOLS_NODE_NAME,
)
from app.application.agents.node_functions.api_tools_node import (
    create_api_tool_executor_node,
    create_tool_calling_agent_node,
)
from app.application.agents.node_functions.book_appintment_node import (
    book_appointment_node,
)
from app.application.agents.node_functions.check_availability_node import (
    check_availability_node,
)
from app.application.agents.node_functions.check_completeness_node import (
    check_completeness_node,
)
from app.application.agents.node_functions.clarification_node import clarification_node
from app.application.agents.node_functions.collection_node import collection_node
from app.application.agents.node_functions.fallback_node import fallback_node
from app.application.agents.node_functions.farewell_node import farewell_node
from app.application.agents.node_functions.final_confirmation_node import (
    final_confirmation_node,
)
from app.application.agents.node_functions.greeting_node import greeting_node
from app.application.agents.node_functions.orquestrator_node import orquestrator_node
from app.application.agents.node_functions.other_node import other_node
from app.application.agents.node_functions.scheduling_info_node import (
    scheduling_info_node,
)
from app.application.agents.node_functions.scheduling_node import scheduling_node
from app.application.agents.node_functions.validate_and_confirm_node import (
    validate_and_confirm_node,
)
from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.agents.tools.medical_api_tools import MedicalApiTools
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient
from app.infrastructure.repositories.apphealth_api_medical_repository import (
    AppHealthAPIMedicalRepository,
)
from app.infrastructure.services.llm.llm_factory import LLMFactory

AGENT_TOOL_CALLER_NODE_NAME = "agent_tool_caller"


class MessageAgentBuilder:
    """
    Builder para criar o agente de mensagem
    """

    def __init__(self, checkpointer: BaseCheckpointSaver):
        """
        Inicializa e constroi o grafo do agente de mensagem
        """
        self.graph = StateGraph(MessageAgentState)
        self.router = MessageRouter()

        # 2. Cliente API e Repositório
        self.apphealth_api_client = AppHealthAPIClient()
        self.apphealth_repository = AppHealthAPIMedicalRepository(
            api_client=self.apphealth_api_client
        )

        # 3. Tools
        self.medical_api_tools = MedicalApiTools(
            medical_repository=self.apphealth_repository,
            api_client=self.apphealth_api_client,
        )

        self._build_graph()
        self._compiled_agent = self.graph.compile(checkpointer=checkpointer)

    def _build_graph(self):
        """
        Adiciona os nós e define as arestas para o workflow do agente.
        """
        self._add_nodes()
        self.graph.set_entry_point("orquestrator_node")
        self._add_edges()

    def _add_nodes(self):
        """
        Constroi os nós do agente de mensagem
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
        self.graph.add_node("check_availability_node", check_availability_node)
        self.graph.add_node("book_appointment_node", book_appointment_node)

        # Instanciar dependências para as Tools e LLM
        self.llm_service = LLMFactory.create_llm_service("openai")

        # Novos nós para Tools
        tool_calling_agent_func = create_tool_calling_agent_node(
            llm_service=self.llm_service,
            medical_api_tools=self.medical_api_tools,
        )
        self.graph.add_node(AGENT_TOOL_CALLER_NODE_NAME, tool_calling_agent_func)

        # Nó que executa a tool (ToolNode do LangGraph)
        tool_executor_func = create_api_tool_executor_node(
            medical_api_tools=self.medical_api_tools
        )
        self.graph.add_node(EXECUTE_MEDICAL_TOOLS_NODE_NAME, tool_executor_func)

    def _add_edges(self):
        """
        Constroi as arestas do agente de mensagem
        """
        # Roteamento inicial do orquestrador
        self.graph.add_conditional_edges(
            "orquestrator_node",
            self.router.route_orquestrator,
            {
                "scheduling_node": "scheduling_node",
                "scheduling_info_node": "scheduling_info_node",
                "final_confirmation_node": "final_confirmation_node",
                "greeting_node": "greeting_node",
                "farewell_node": "farewell_node",
                "other_node": "other_node",
                "clarification_node": "clarification_node",
                AGENT_TOOL_CALLER_NODE_NAME: AGENT_TOOL_CALLER_NODE_NAME,
                "fallback_node": "fallback_node",
                "book_appointment_node": "book_appointment_node",
            },
        )

        # Fluxo das Tools
        self.graph.add_conditional_edges(
            AGENT_TOOL_CALLER_NODE_NAME,
            self.router.decide_after_tool_agent,
            {
                EXECUTE_MEDICAL_TOOLS_NODE_NAME: EXECUTE_MEDICAL_TOOLS_NODE_NAME,
                "END": END,
                "fallback_node": "fallback_node",
                "validate_and_confirm_node": "validate_and_confirm_node",
            },
        )

        self.graph.add_edge(EXECUTE_MEDICAL_TOOLS_NODE_NAME, AGENT_TOOL_CALLER_NODE_NAME)

        self.graph.add_edge("scheduling_node", "collection_node")
        self.graph.add_edge("collection_node", "clarification_node")

        self.graph.add_conditional_edges(
            "scheduling_info_node",
            lambda state: state.get("next_step", "clarification_node"),
            {
                "check_completeness": "check_completeness_node",
                "clarification": "clarification_node",
                "clarification_node": "clarification_node",
                "check_availability_node": "check_availability_node",
                AGENT_TOOL_CALLER_NODE_NAME: AGENT_TOOL_CALLER_NODE_NAME,
            },
        )

        self.graph.add_conditional_edges(
            "check_completeness_node",
            self.router.route_after_completeness_check,
            {
                "clarification_node": "clarification_node",
                "check_availability_node": "check_availability_node",
            },
        )

        self.graph.add_conditional_edges(
            "validate_and_confirm_node",
            lambda state: state.get("next_step", "clarification_node"),
            {
                "awaiting_final_confirmation": END,
                "clarification_node": "clarification_node",
            },
        )

        self.graph.add_conditional_edges(
            "final_confirmation_node",
            lambda state: state.get("next_step", "completed"),
            {
                # ALTERAÇÃO AQUI: Em vez de END, vai para a verificação de agenda!
                "appointment_confirmed": "check_availability_node",
                "awaiting_correction": END,
                "awaiting_final_confirmation": END,
                "completed": END,
            },
        )

        # Roteamento condicional após check_availability_node
        self.graph.add_conditional_edges(
            "check_availability_node",
            self.router.route_after_check_availability,
            {"END": END, "agent_tool_caller": "agent_tool_caller"},
        )

        self.graph.add_edge("book_appointment_node", END)

        self.graph.add_conditional_edges(
            "clarification_node",
            self.router.decide_after_clarification,
            {
                "END_AWAITING_USER": END,
                "book_appointment_node": "book_appointment_node",
                "check_availability_node": "check_availability_node",
                "DEFAULT_END": END,
            },
        )

        # Nós finais simples
        self.graph.add_edge("greeting_node", END)
        self.graph.add_edge("other_node", END)
        self.graph.add_edge("fallback_node", END)
        self.graph.add_edge("farewell_node", END)

    def _route_after_availability_check(self, state):
        """
        Decide o que fazer após check_availability_node.
        """
        conversation_context = state.get("conversation_context", "").lower()

        if conversation_context == "awaiting_date_selection":
            return "awaiting_date_selection"
        else:
            return "completed"

    def build_agent(self):
        """
        Compila e retorna o agente de mensagem.
        """
        try:
            print("--- Mermaid Diagram do Agente ---")
            print(self._compiled_agent.get_graph().draw_mermaid())
            print("---------------------------------")
        except Exception as e:
            print(
                f"Erro ao gerar diagrama Mermaid: {e} (Pode precisar de `pip install pygraphviz` ou `mermaid-cli`)"
            )

        return self._compiled_agent


async def get_message_agent():
    from app.infrastructure.persistence.mongodb_saver_checkpointer import (
        MongoDBSaverCheckpointer,
    )

    mongodb_provider = MongoDBSaverCheckpointer()
    actual_mongo_checkpointer = mongodb_provider.create_checkpoint()

    builder = MessageAgentBuilder(checkpointer=actual_mongo_checkpointer)
    agent = builder.build_agent()
    return agent
