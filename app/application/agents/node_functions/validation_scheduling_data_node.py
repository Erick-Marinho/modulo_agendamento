import json
import logging

from typing import List, Optional
from langchain_core.messages import AIMessage

from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.interfaces.illm_service import ILLMService
from app.infrastructure.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

def validation_scheduling_data_node(state: MessageAgentState) -> MessageAgentState:
    logger.info(f"Estado atual do agente: {state}")
    print(f"Estado atual do agente: {state}")
    """
        Nó responsavel por solicitar ao paciente, a validação dos dados de agendamento
    """
    new_state = {}
    
    ai_response_text = "Por favor confirme se os dados do agendamento estão corretos! Me informe se você quer fazer alguma alteração!"
    new_state = {
        "messages": [AIMessage(content=ai_response_text)],
        "next_step": "END_AWAITING_USER_VALIDATION"
    }
        
    return {
        **state,
        **new_state,
    }
        