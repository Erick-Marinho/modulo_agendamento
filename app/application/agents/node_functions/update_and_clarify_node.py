import logging
from app.application.agents.state.message_agent_state import MessageAgentState
from app.domain.sheduling_details import SchedulingDetails
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import AIMessage


logger = logging.getLogger(__name__)

def update_and_clarify_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó identifica dados que o usuario quer modificar, 
    atualiza o estado e retorna um JSON com o novo estado e uma mensagem 
    caso o usuario nao tenha informado algum dado
    """

    logger.info("Iniciando fluxo de alteração e confirmação")

    llm_type = "openai"
    llm_service = LLMFactory.create_llm_service(llm_type)
    
    scheduling_details = state.get("extracted_scheduling_details")
    user_message = state.get("message")

    llm_response = llm_service.update_scheduling_datails(scheduling_details, user_message)

    if llm_response.get("question"):
        return {
            "messages": [AIMessage(content=llm_response.get("question"))],
            "next_step": "END_AWAITING_USER_FOR_DATA"
        }

    new_scheduling_details: SchedulingDetails = llm_response.get("new_state")

    new_state: MessageAgentState = {
        **state,
        "extracted_scheduling_details": new_scheduling_details,
        "next_step": "PROCEED_TO_VALIDATION"
    }


    return new_state
    

