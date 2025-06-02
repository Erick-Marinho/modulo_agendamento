from app.application.agents.state.message_agent_state import MessageAgentState
from langchain_core.messages import AIMessage

def greeting_node(state: MessageAgentState) -> dict:
    """
    Função para processar a mensagem de boas vindas
    """
    current_message = state["messages"]
    last_message = current_message[-1]

    user_text = last_message.content

    print(f"User text: {user_text}")

    ai_response_text = "Olá, como posso ajudar você?"
    
    return {
        "messages": [AIMessage(content=ai_response_text)],
        "next_step": "orquestrator_node"
    }

