from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MessageAgentState(TypedDict):
    """
    Representa o estado do agente de mensagem
    """
    
    message: str
    phone_number: str
    message_id: str
    

    messages: Annotated[list[BaseMessage], add_messages]


    