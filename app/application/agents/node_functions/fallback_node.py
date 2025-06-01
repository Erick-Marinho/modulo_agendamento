from langchain_core.messages import AIMessage
from app.application.agents.state.message_agent_state import MessageAgentState


def fallback_node(state: MessageAgentState) -> MessageAgentState:
    ai_response_text = "Desculpe, não entendi o que você disse. Por favor, tente novamente."
    
    return {
        "messages": [AIMessage(content=ai_response_text)],
        "next_step": "fallback_node"
    }

