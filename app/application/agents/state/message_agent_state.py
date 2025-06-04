from typing import Annotated, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from app.domain.sheduling_details import SchedulingDetails


class MessageAgentState(TypedDict):
    """
    Representa o estado do agente de mensagem
    """
    # Mensagens da conversa
    messages: Annotated[list[BaseMessage], add_messages]

    # Mensagens do usuário
    message: str
    phone_number: str
    message_id: str

    # Detalhes de agendamento
    extracted_scheduling_details: Optional[SchedulingDetails]
    missing_fields: Optional[List[str]]

    # Controle de fluxo
    next_step: str

    # Contexto da conversa
    conversation_context: Optional[str]
    awaiting_user_input: Optional[bool]
