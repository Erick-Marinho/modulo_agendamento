from app.application.agents.state.message_agent_state import MessageAgentState
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
    ai_response_text = (
        "Posso ajudar com informações gerais sobre nossa clínica. "
        "Para agendamentos, me informe a especialidade, profissional, data e horário desejados. "
        "Para outras dúvidas, entre em contato conosco diretamente."
    )
    
    updated_messages = current_messages + [AIMessage(content=ai_response_text)]
    
    return {
        **state, 
        "messages": updated_messages,
        "next_step": "completed"
    }