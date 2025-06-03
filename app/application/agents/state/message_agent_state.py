from typing import Annotated, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from app.domain.sheduling_details import SchedulingDetails


class MessageAgentState(TypedDict):
    """
    Representa o estado do agente de mensagem
    """
    messages: Annotated[list[BaseMessage], add_messages]
    
    message: str
    phone_number: str
    message_id: str

    extracted_scheduling_details: Optional[SchedulingDetails]

    next_step: str
