import json
import logging

from typing import List, Optional
from langchain_core.messages import AIMessage

from app.application.agents.state.message_agent_state import MessageAgentState
from app.application.interfaces.illm_service import ILLMService
from app.infrastructure.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

# def validation_scheduling_data_node(state: MessageAgentState) -> MessageAgentState:
#     logger.info(f"Estado atual do agente: {state}")
#     print(f"Estado atual do agente: {state}")
#     """
#         Nó responsavel por solicitar ao paciente, a validação dos dados de agendamento
#     """
#     new_state = {}
    
#     ai_response_text = "Por favor confirme se os dados do agendamento estão corretos! Me informe se você quer fazer alguma alteração!"
#     new_state = {
#         "messages": [AIMessage(content=ai_response_text)],
#         "next_step": "END_AWAITING_USER_VALIDATION"
#     }
        
#     return {
#         **state,
#         **new_state,
#     }
        
def validation_scheduling_data_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó responsável por validar os dados coletados e gerar uma confirmação para o usuário.
    """
    logger.info("--- Executando nó validate_and_confirm ---")
   
    extracted_details = state.get("extracted_scheduling_details")
    current_messages = state.get("messages", [])
   
    if not extracted_details:
        logger.error("Nenhum detalhe extraído encontrado para validação")
        return {**state, "next_step": "clarification"}
   
    try:
        confirmation_message = _generate_confirmation_message(extracted_details)
       
        updated_messages = current_messages + [AIMessage(content=confirmation_message)]
       
        logger.info(f"Mensagem de confirmação gerada: {confirmation_message}")
       
        return {
            **state,
            "messages": updated_messages,
            "next_step": "END_AWAITING_USER_VALIDATION"
        }
       
    except Exception as e:
        logger.error(f"Erro ao validar e confirmar: {e}")
        return {**state, "next_step": "clarification"}
    

def _generate_confirmation_message(details) -> str:
    """
    Gera uma mensagem de confirmação baseada nos detalhes extraídos.
    """
    try:
        llm_service = LLMFactory.create_llm_service("openai")
        return llm_service.generate_confirmation_message(details)
    except Exception as e:
        logger.error(f"Erro ao gerar mensagem via LLM: {e}")
        return _generate_simple_confirmation(details)
 

def _generate_simple_confirmation(details) -> str:
    """
    Gera uma confirmação simples como fallback.
    """
    parts = ["Vou confirmar os dados do seu agendamento:"]
   
    if details.service_type:
        parts.append(f"• Tipo: {details.service_type}")
   
    if details.professional_name:
        parts.append(f"• Profissional: {details.professional_name}")
    elif details.specialty:
        parts.append(f"• Especialidade: {details.specialty}")
   
    if details.date_preference:
        parts.append(f"• Data: {details.date_preference}")
   
    if details.time_preference:
        parts.append(f"• Horário: {details.time_preference}")
   
    parts.append("\nEstão corretas essas informações? Responda 'sim' para confirmar ou me informe o que precisa ser alterado.")
   
    return "\n".join(parts)