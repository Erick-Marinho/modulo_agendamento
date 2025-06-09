from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import AIMessage
import logging

logger = logging.getLogger(__name__)


def other_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó responsável por responder perguntas gerais sobre a clínica que não são agendamentos.
    """
    logger.info("--- Executando nó other ---")

    current_messages = state.get("messages", [])

    # Por enquanto, uma resposta simples
    # No futuro, aqui podemos integrar informações reais da clínica
    try:
        llm_service = LLMFactory.create_llm_service("openai")
        ai_response_text = llm_service.generate_general_help_message()
    except Exception as e:
        logger.error(f"Erro ao gerar mensagem de ajuda via IA: {e}")
        ai_response_text = (
            "Posso ajudar com agendamentos. Informe profissional, data e horário."
        )

    updated_messages = current_messages + [AIMessage(content=ai_response_text)]

    return {**state, "messages": updated_messages, "next_step": "completed"}
