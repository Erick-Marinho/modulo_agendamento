from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import AIMessage, HumanMessage
import logging

logger = logging.getLogger(__name__)

def final_confirmation_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó que processa a resposta final do usuário à confirmação.
    """
    logger.info("--- Executando nó final_confirmation ---")
    
    current_messages = state.get("messages", [])
    last_user_message = _get_last_user_message(current_messages)
    
    if not last_user_message:
        logger.warning("Nenhuma mensagem do usuário encontrada")
        return {**state, "next_step": "awaiting_final_confirmation"}
    
    logger.info(f"Processando confirmação final: '{last_user_message}'")
    
    # Classifica a resposta do usuário
    confirmation_result = _classify_confirmation_response(last_user_message)
    
    if confirmation_result == "confirmed":
        return _handle_confirmed_appointment(state)
    elif confirmation_result == "simple_rejection":
        return _handle_simple_rejection(state)
    elif confirmation_result == "correction_with_data":
        return _handle_correction_with_data(state)
    else:
        return _handle_unclear_response(state)

def _get_last_user_message(messages):
    """Obtém a última mensagem do usuário."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return None

def _classify_confirmation_response(message: str) -> str:
    """
    Classifica a resposta do usuário usando LLM para maior precisão.
    """
    try:
        llm_service = LLMFactory.create_llm_service("openai")
        classification = llm_service.classify_confirmation_response(message)
        logger.info(f"🤖 LLM classificou '{message}' como: '{classification}'")
        return classification
        
    except Exception as e:
        logger.error(f"Erro na classificação LLM, usando fallback: {e}")
        return _classify_confirmation_response_fallback(message)
    
def _classify_confirmation_response_fallback(message: str) -> str:
    """
    Fallback simples caso o LLM falhe.
    """
    message_lower = message.lower().strip()
    
    if message_lower in ["sim", "ok", "correto", "certo", "perfeito", "isso mesmo"]:
        return "confirmed"
    
    if message_lower in ["não", "nao", "quero mudar", "quero alterar", "preciso alterar"]:
        return "simple_rejection"
    
    has_numbers = any(char.isdigit() for char in message_lower)
    has_specific_data = any(word in message_lower for word in [
        "para", "dr", "dra", "manhã", "tarde", "noite", 
        "segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo",
        "cardiologia", "pediatria", "ortopedia", "h", ":"
    ])
    
    if has_numbers or has_specific_data:
        return "correction_with_data"
    
    return "unclear"


def _handle_confirmed_appointment(state: MessageAgentState) -> MessageAgentState:
    """
    Lida com agendamento confirmado.
    """
    logger.info("Agendamento confirmado pelo usuário")
    
    current_messages = state.get("messages", [])
    
    try:
        llm_service = LLMFactory.create_llm_service("openai")
        success_message = llm_service.generate_success_message()
    except Exception as e:
        logger.error(f"Erro ao gerar mensagem de sucesso via IA: {e}")
        success_message = "Dados confirmados com sucesso!"
    
    updated_messages = current_messages + [AIMessage(content=success_message)]
    
    return {
        **state,
        "messages": updated_messages,
        "next_step": "appointment_confirmed"
    }

def _handle_unclear_response(state: MessageAgentState) -> MessageAgentState:
    """
    Lida com resposta não clara do usuário.
    """
    logger.info("Resposta do usuário não foi clara")
    
    current_messages = state.get("messages", [])
    
    try:
        llm_service = LLMFactory.create_llm_service("openai")
        clarification_message = llm_service.generate_unclear_response_message()
    except Exception as e:
        logger.error(f"Erro ao gerar mensagem de esclarecimento via IA: {e}")
        clarification_message = "Confirma os dados? Responda 'sim' ou 'não'."
    
    updated_messages = current_messages + [AIMessage(content=clarification_message)]
    
    return {
        **state,
        "messages": updated_messages,
        "next_step": "awaiting_final_confirmation"
    }

def _handle_simple_rejection(state: MessageAgentState) -> MessageAgentState:
    """
    Usuário quer alterar mas não especificou o que.
    """
    logger.info("Usuário quer alterar mas não especificou dados")
    
    current_messages = state.get("messages", [])
    
    try:
        llm_service = LLMFactory.create_llm_service("openai")
        correction_message = llm_service.generate_correction_request_message()
    except Exception as e:
        logger.error(f"Erro ao gerar mensagem de correção via IA: {e}")
        correction_message = "Me informe o que gostaria de alterar."
    
    updated_messages = current_messages + [AIMessage(content=correction_message)]
    
    return {
        **state,
        "messages": updated_messages,
        "next_step": "awaiting_correction"
    }

def _handle_correction_with_data(state: MessageAgentState) -> MessageAgentState:
    """
    Usuário já forneceu dados para correção - processa diretamente.
    """
    logger.info("Usuário forneceu dados de correção diretamente - processando")
    
    return {
        **state,
        "next_step": "scheduling_info"
    }