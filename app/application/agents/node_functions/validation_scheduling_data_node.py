import logging

from typing import List, Optional
from langchain_core.messages import AIMessage

from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.interfaces.illm_service import ILLMService
from app.infrastructure.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

def validation_scheduling_data_node(state: MessageAgentState) -> MessageAgentState:
    logger.info(f"Estado atual do agente BLABLABLA: {state}")
    print(f"Estado atual do agente: {state}")
    """
        Nó responsavel por solicitar ao paciente, a validação dos dados de agendamento
    """
    new_state = {}
    
    if state.get("next_step") == "PROCEED_TO_VALIDATION":
        ai_response_text = "Por favor confirme se os dados do agendamento estão corretos! Me informe se você quer fazer alguma alteração?"
        new_state = {
            "messages": [AIMessage(content=ai_response_text)],
            "next_step": "END_AWAITING_USER_VALIDATION"
        }
    
    llm_type = "openai"
    llm_service: ILLMService = LLMFactory.create_llm_service(llm_type)

    print("AAAAAAAAAAAAAAAAA", state)
    
    ia_response_json = llm_service.validate_scheduling_user_confirmation(user_message=state.get("message"))
    # next_step = ia_response_json.get("intent", "DEFAULT_END")

    print("RESULTADO UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU", ia_response_json)



    return {
        **state,
        **new_state,
        "next_step": "DEFAULT_END"
    }
    


    # return {
    #     **state,
    #     "next_step": next_step
    # } 

    