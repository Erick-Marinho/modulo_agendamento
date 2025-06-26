from app.application.agents.state.message_agent_state import MessageAgentState
from langchain_core.messages import AIMessage


def farewell_node(state: MessageAgentState) -> dict:
    """
    Função para processar a mensagem de despedida
    """
    current_messages = state.get("messages", [])
    conversation_context = state.get("conversation_context", "")
    
    last_message = current_messages[-1] if current_messages else None

    if last_message:
        user_text = last_message.content
        print(f"User text: {user_text}")

    # 🔧 CORREÇÃO: Se contexto é "conversation_ended", orquestrador já enviou despedida
    if conversation_context == "conversation_ended":
        # Não enviar mensagem adicional, apenas finalizar
        return {
            **state,
            "next_step": "completed",
        }
    
    # Enviar mensagem genérica apenas se não foi enviada despedida personalizada
    ai_response_text = (
        "Até mais! Foi um prazer ajudar você. Volte sempre que precisar!"
    )

    # Adicionar à conversa em vez de sobrescrever
    updated_messages = current_messages + [AIMessage(content=ai_response_text)]

    return {
        **state,  # Preservar todo o estado
        "messages": updated_messages,
        "next_step": "completed",  # Finalizar após despedida
    }
