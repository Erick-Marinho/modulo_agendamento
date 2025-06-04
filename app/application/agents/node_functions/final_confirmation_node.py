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
    elif confirmation_result == "rejected":
        return _handle_rejected_appointment(state)
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
    Classifica a resposta do usuário como confirmada, rejeitada ou unclear.
    """
    message_lower = message.lower().strip()
    
    # Palavras que indicam confirmação
    confirm_words = ["sim", "confirmar", "confirmo", "correto", "certo", "ok", "perfeito", "isso mesmo"]
    
    # Palavras que indicam rejeição/correção
    reject_words = ["não", "nao", "errado", "incorreto", "mudar", "alterar", "corrigir"]
    
    if any(word in message_lower for word in confirm_words):
        return "confirmed"
    elif any(word in message_lower for word in reject_words):
        return "rejected"
    else:
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

def _handle_rejected_appointment(state: MessageAgentState) -> MessageAgentState:
    """
    Lida com agendamento rejeitado/correção solicitada.
    """
    logger.info("Usuário solicitou correção no agendamento")
    
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