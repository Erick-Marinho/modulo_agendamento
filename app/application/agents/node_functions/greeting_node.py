from app.application.agents.state.message_agent_state import MessageAgentState
from langchain_core.messages import AIMessage


def greeting_node(state: MessageAgentState) -> dict:
    """
    Função para processar a mensagem de boas vindas
    """
    current_messages = state.get("messages", [])
    last_message = current_messages[-1] if current_messages else None

    if last_message:
        user_text = last_message.content
        print(f"User text: {user_text}")

    ai_response_text = "Olá! Como posso ajudar você hoje? Posso ajudar com agendamentos médicos ou informações sobre especialidades disponíveis."

    updated_messages = current_messages + [AIMessage(content=ai_response_text)]

    return {**state, "messages": updated_messages, "next_step": "completed"}
