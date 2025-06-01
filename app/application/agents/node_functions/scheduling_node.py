from langchain_core.messages import AIMessage
from app.application.agents.state.message_agent_state import MessageAgentState

def scheduling_node(state: MessageAgentState) -> MessageAgentState:
    print("Agendamento iniciado")

    ai_response_text = "Agendamento iniciado"
    
    return {
        "messages": [AIMessage(content=ai_response_text)],
        "next_step": "scheduling"
    }
