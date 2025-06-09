import logging

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

AGENT_TOOL_CALLER_NODE_NAME = "agent_tool_caller"


def orquestrator_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó orquestrador que classifica a intenção do usuário e define o próximo passo.
    """
    logger.info(f"--- Executando nó orquestrador ---")

    current_next_step = state.get("next_step", "")
    if current_next_step == "awaiting_final_confirmation":
        logger.info("Estado indica que estamos aguardando confirmação final")
        return {**state, "next_step": "final_confirmation"}

    if current_next_step == "awaiting_correction":
        logger.info(
            "Estado indica que estamos aguardando correção - direcionando para scheduling_info"
        )
        return {
            **state,
            "next_step": "scheduling_info",
            "conversation_context": "correcting_data",
        }

    conversation_context = state.get("conversation_context")

    # Se o usuário está selecionando um HORÁRIO, vá para o agendamento final.
    if conversation_context == "awaiting_slot_selection":
        logger.info(
            f"Contexto é '{conversation_context}', direcionando para o agendamento final."
        )
        return {**state, "next_step": "book_appointment_node"}

    # Se o usuário está selecionando uma nova DATA, volte para a coleta de informações.
    if conversation_context == "awaiting_new_date_selection":
        logger.info(
            f"Contexto é '{conversation_context}', direcionando para a coleta de informações (scheduling_info)."
        )
        return {**state, "next_step": "scheduling_info"}

    messages = state.get("messages", [])
    last_human_message_content = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message_content = msg.content
            break

    if not last_human_message_content:
        logger.warning(
            "Nenhuma mensagem humana encontrada no estado para o orquestrador."
        )
        if state.get("message"):
            last_human_message_content = state.get("message")
        else:
            logger.warning("Orquestrador: Nenhuma mensagem humana para classificar.")
            return {
                **state,
                "next_step": "unclear",
                "conversation_context": "system_error",
            }

    logger.info(f"Orquestrador classificando mensagem: '{last_human_message_content}'")

    try:
        llm_service = LLMFactory.create_llm_service("openai")
        classification = llm_service.classify_message(last_human_message_content)

        classification = classification.strip().lower()
        logger.info(
            f"Classificação retornada pelo LLM para orquestrador: '{classification}'"
        )

        valid_classifications = [
            "scheduling",
            "scheduling_info",
            "greeting",
            "farewell",
            "api_query",
            "other",
            "unclear",
        ]

        if classification not in valid_classifications:
            logger.warning(
                f"Classificação inválida do LLM: '{classification}'. Usando 'unclear' como fallback."
            )
            classification = "unclear"

        next_step_map = {
            "scheduling": "scheduling",
            "scheduling_info": "scheduling_info",
            "greeting": "greeting",
            "farewell": "farewell",
            "api_query": AGENT_TOOL_CALLER_NODE_NAME,
            "other": "other",
            "unclear": "fallback_node",
        }

        next_node = next_step_map.get(classification, "fallback_node")

        new_conversation_context = classification
        if classification in ["scheduling", "scheduling_info"]:
            new_conversation_context = "scheduling_flow"
        elif classification == "api_query":
            new_conversation_context = "api_interaction"

        logger.info(
            f"Orquestrador definiu next_step para: '{next_node}' com contexto: '{new_conversation_context}'"
        )
        return {
            **state,
            "next_step": next_node,
            "conversation_context": new_conversation_context,
        }

    except Exception as e:
        logger.error(
            f"Erro ao classificar mensagem no orquestrador: {e}", exc_info=True
        )
        return {
            **state,
            "next_step": "fallback_node",
            "conversation_context": "system_error",
        }
