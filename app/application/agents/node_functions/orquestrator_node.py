import logging

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)


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
        logger.info("Estado indica que estamos aguardando correção - direcionando para scheduling_info")
        return {**state, "next_step": "scheduling_info",  "conversation_context": "correcting_data"}

    # Verifica se estamos em um contexto específico
    conversation_context = state.get("conversation_context")

    if conversation_context == "awaiting_confirmation":
        logger.info("Usuário está respondendo a uma confirmação")
        return {**state, "next_step": "final_confirmation"}

    # Pega a última mensagem do usuário
    messages = state.get("messages", [])
    
    # Verifica se a última mensagem do assistente estava pedindo confirmação
    if len(messages) >= 2:
        last_ai_message = None
        for msg in reversed(messages[:-1]):  # Exclui a última (que deve ser do usuário)
            if isinstance(msg, AIMessage):
                last_ai_message = msg.content.lower()
                break
        
        if last_ai_message and ("alterar" in last_ai_message or "corrigir" in last_ai_message):
            logger.info("Detectado contexto de confirmação na conversa")
            return {**state, "next_step": "sheduling_info", "conversation_context": "sheduling"}
    
    # Encontra a última mensagem humana
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
        
        context = None
        if classification in ["scheduling", "scheduling_info"]:
            context = "scheduling"
        
        return {**state, "next_step": classification, "conversation_context": context}
        
    except Exception as e:
        logger.error(f"Erro ao classificar mensagem: {e}")
        return {**state, "next_step": "unclear"}