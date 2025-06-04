import logging

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def orquestrator_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó orquestrador que classifica a intenção do usuário e define o próximo passo.
    """

    logger.info(f"--- Executando nó orquestrador ---")

    messages = state.get("messages", [])

    if not messages:
        logger.warning("Nenhuma mensagem encontrada no estado.")
        return {**state, "next_step": "unclear"}
    
    last_human_message = None

    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break

    if not last_human_message:
        logger.warning("Nenhuma mensagem humana encontrada no estado.")
        return {**state, "next_step": "unclear"}
    
    logger.info(f"Classificando mensagem: {last_human_message}")

    try:
        llm_service = LLMFactory.create_llm_service("openai")
        classification = llm_service.classify_message(last_human_message)
        
        classification = classification.strip().lower()
        
        logger.info(f"Classificação retornada pelo LLM: '{classification}'")
        
        valid_classifications = ["scheduling", "scheduling_info", "greeting", "farewell", "other", "unclear"]
        
        if classification not in valid_classifications:
            logger.warning(f"Classificação inválida: '{classification}'. Usando 'unclear' como fallback.")
            classification = "unclear"
        
        return {**state, "next_step": classification}
        
    except Exception as e:
        logger.error(f"Erro ao classificar mensagem: {e}")
        return {**state, "next_step": "unclear"}