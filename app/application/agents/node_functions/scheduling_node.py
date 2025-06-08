import copy
import logging
from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import AIMessage


logger = logging.getLogger(__name__)

def scheduling_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó que inicia o fluxo de agendamento.
    Prepara para a coleta de informações e passa o estado adiante.
    """
    logger.info("Iniciando fluxo de agendamento")

    llm_type = "openai"
    llm_service = LLMFactory.create_llm_service(llm_type)

    conversation_history = state.get("messages")
    user_message = state.get("message")
    existing_scheduling_details = state.get("extracted_scheduling_details")
    
    user_intent = llm_service.analyze_user_intent(conversation_history, user_message, existing_scheduling_details)
    
    new_state: MessageAgentState = {
        **state,
        "next_step": user_intent
    }
    
    if user_intent == "UPDATE_WITHOUT_DATA":
        new_state["messages"] = [AIMessage(content="Percebemos que você quer atualizar algo, mas não temos dados existentes para atualizar. Você quer iniciar um agendamento?")]

    return new_state
