import logging
from typing import Optional
from app.application.agents.state.message_agent_state import MessageAgentState
from app.domain.sheduling_details import SchedulingDetails
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import AIMessage, HumanMessage


logger = logging.getLogger(__name__)

def update_and_clarify_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó identifica dados que o usuario quer modificar, 
    atualiza o estado e retorna um JSON com o novo estado e uma mensagem 
    caso o usuario nao tenha informado algum dado
    """

    logger.info("Iniciando fluxo de alteração e confirmação")

    current_messages = state.get("messages", [])
    last_user_message = _get_last_user_message(current_messages)

    if not last_user_message:
        logger.warning("Não foi possível identificar a última mensagem do usuário")
        return {
            **state,
            "next_step": "END_AWAITING_USER_FOR_DATA"
        }
    
    confirmation_result = _classify_confirmation_response(last_user_message)

    if confirmation_result == "confirmed":
        return _handle_confirmed_appointment(state)
    elif confirmation_result == "simple_rejection":
        return _handle_simple_rejection(state)
    elif confirmation_result == "correction_with_data":
        return _handle_correction_with_data(state)
    else:
        return _handle_unclear_response(state)


def _get_last_user_message(messages: str) -> str:

    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
        
    return None
    

def _classify_confirmation_response(user_message: str) -> str:
    """
    Classifica a resposta do usuário como confirmação ou não
    """
    
    try:
        llm_type = "openai"
        llm_service = LLMFactory.create_llm_service(llm_type)

        classification = llm_service.classification_confirmation_response(user_message)

        return classification


    except Exception as e:
        logger.error(f"Erro ao classificar a resposta do usuário: {e}")
        return "unclear"

def _handle_confirmed_appointment(state: MessageAgentState) -> MessageAgentState:
    current_messages = state.get("messages", [])


    try:
        llm_type = "openai"
        llm_service = LLMFactory.create_llm_service(llm_type)

        success_message = llm_service.generate_success_message()

    except Exception as e:
        logger.error(f"Erro ao gerar mensagem de sucesso: {e}")
        success_message = "Dados recebidos com sucesso!"

    update_message = current_messages + [AIMessage(content=success_message)]

    return {
        **state,
        "messages": update_message,
        "next_step": "DEFAULT_END"
    }

def _handle_simple_rejection(state: MessageAgentState) -> MessageAgentState:
    current_messages = state.get("messages", [])

    last_user_message = _get_last_user_message(current_messages)

    correction_message_text = ""

    target_field = _identify_target_field_from_rejection(last_user_message)

    if target_field == "horário":
        correction_message_text = "Entendi que você gostaria de alterar o horário. Qual o novo horário de sua preferência (manhã ou tarde, ou o horário específico)?"
    elif target_field == "data":
        correction_message_text = "Certo. Para qual nova data você gostaria de agendar?"
    elif target_field == "profissional":
        correction_message_text = "Ok. Qual o nome do novo profissional que você gostaria de consultar?"
    elif target_field == "especialidade":
        correction_message_text = "Entendido. Qual a nova especialidade que você procura?"
    else:
        logger.info(f"Campo específico para correção não identificado em '{last_user_message}'. Usando pergunta genérica.")
        try:
            llm_service = LLMFactory.create_llm_service("openai")
            correction_message_text = llm_service.generate_correction_request_message()
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de correção genérica via IA: {e}")
            correction_message_text = "Entendi que você quer alterar algo. Por favor, me informe especificamente o que gostaria de mudar (por exemplo, data, horário, profissional ou especialidade)."
   
    updated_messages = current_messages + [AIMessage(content=correction_message_text)]
   
    return {
        **state,
        "messages": updated_messages,
        "next_step": "END_AWAITING_USER_FOR_DATA"
    }

def _handle_correction_with_data(state: MessageAgentState) -> MessageAgentState:
    extracted_details = state.get("extracted_scheduling_details")

    try:
        llm_type = "openai"
        llm_service = LLMFactory.create_llm_service(llm_type)

        all_messages = state.get("messages", [])

        if not all_messages:
            logger.warning("Não há mensagens para processar")
            return {
                **state,
                "next_step": "DEFAULT_END"
            }
        
        conversation_history = _format_conversation_history(all_messages)
        new_details = llm_service.extract_scheduling_details(conversation_history)

        if new_details:
            updated_datails = _merge_scheduling_details(extracted_details, new_details)

            return {
                **state,
                "extracted_scheduling_details": updated_datails,
                "next_step": "PROCEED_TO_VALIDATION"
            }
    
    except Exception as e:
        logger.error(f"Erro ao processar mensagens: {e}")
        return {
            **state,
            "next_step": "DEFAULT_END"
        }
    
    return {
        **state,
        "next_step": "PROCEED_TO_VALIDATION"
    }
 

def _identify_target_field_from_rejection(user_message: str) -> str:

    if not user_message:
        return None
    
    message_lower = user_message.lower().strip()
    keywords_map = {
        "horário": ["horario", "hora", "horas", "turno"],
        "data": ["data", "dia"],
        "profissional": ["médico", "medico", "profissional", "doutor", "doutora", "dr", "dra"],
        "especialidade": ["especialidade"],
    }

    for field, field_keywords in keywords_map.items():
        if any(keyword in message_lower for keyword in field_keywords):
            return field
        
    return None


def _format_conversation_history(messages, max_messages: int = 5) -> str:
    if not messages:
        return "Nenhuma conversa ainda"
    
    recent_messages = messages[-max_messages:]

    formatted_history = []

    for msg in recent_messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        formatted_history.append(f"{role}: {msg.content}")

    return "\n".join(formatted_history)


def _merge_scheduling_details(previous_details: Optional[SchedulingDetails], new_details: Optional[SchedulingDetails]) -> SchedulingDetails:

    if not previous_details:
        return new_details
    
    if not new_details:
        return previous_details
    
    merged = SchedulingDetails(
        professional_name=new_details.professional_name or previous_details.professional_name,
        specialty=new_details.specialty or previous_details.specialty,
        date_preference=new_details.date_preference or previous_details.date_preference,
        time_preference=new_details.time_preference or previous_details.time_preference,
        service_type=new_details.service_type or previous_details.service_type,
    )

    return merged


def _handle_unclear_response(state: MessageAgentState) -> MessageAgentState:
    """
    Lida com resposta não clara do usuário.
    """
    logger.info("Resposta do usuário não foi clara")
   
    current_messages = state.get("messages", [])

    default_message = "Não consegui entender sua resposta. Por favor, confirme se os dados estão corretos."
   
    # try:
    #     llm_service = LLMFactory.create_llm_service("openai")
    #     clarification_message = llm_service.generate_unclear_response_message()
    # except Exception as e:
    #     logger.error(f"Erro ao gerar mensagem de esclarecimento via IA: {e}")
    #     clarification_message = "Confirma os dados? Responda 'sim' ou 'não'."
   
    updated_messages = current_messages + [AIMessage(content=default_message)]
   
    return {
        **state,
        "messages": updated_messages,
        "next_step": "END_AWAITING_USER_VALIDATION"
    }