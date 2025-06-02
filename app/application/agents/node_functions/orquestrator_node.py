from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory

import logging

logger = logging.getLogger(__name__)


def orquestrator_node(state: MessageAgentState) -> MessageAgentState:

    last_message = state.get("messages")[-1].content.lower()

    print(f"Last message: {last_message}")

    llm = "openai"

    llm_service = LLMFactory.create_llm_service(llm)

    classification = llm_service.classify_message(last_message)

    logger.info(f"Classificação retornada pelo LLM: {classification}")
    
    state["next_step"] = classification
    
    return state