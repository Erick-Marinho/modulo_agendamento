from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.services.llm.llm_factory import LLMFactory
from langchain_core.messages import AIMessage, HumanMessage
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def final_confirmation_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó que processa a resposta final do usuário à confirmação.
    """
    logger.info("--- Executando nó final_confirmation ---")

    current_messages = state.get("messages", [])
    last_user_message = _get_last_user_message(current_messages)

    if not last_user_message:
        logger.warning("Nenhuma mensagem do usuário encontrada")
        return {**state, "next_step": "awaiting_final_confirmation"}

    logger.info(f"Processando confirmação final: '{last_user_message}'")

    # Classifica a resposta do usuário
    confirmation_result = _classify_confirmation_response(last_user_message)

    if confirmation_result == "confirmed":
        return _handle_confirmed_appointment(state)
    elif confirmation_result == "simple_rejection":
        return _handle_simple_rejection(state)
    elif confirmation_result == "correction_with_data":
        return _handle_correction_with_data(state)
    else:
        return _handle_unclear_response(state)


def _get_last_user_message(messages):
    """Obtém a última mensagem do usuário."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return None


def _classify_confirmation_response(message: str) -> str:
    """
    Classifica a resposta do usuário usando LLM para maior precisão.
    """
    try:
        llm_service = LLMFactory.create_llm_service("openai")
        classification = llm_service.classify_confirmation_response(message)
        logger.info(f"LLM classificou '{message}' como: '{classification}'")
        return classification

    except Exception as e:
        logger.error(f"Erro na classificação LLM, usando fallback: {e}")
        return _classify_confirmation_response_fallback(message)


def _classify_confirmation_response_fallback(message: str) -> str:
    """
    Fallback simples caso o LLM falhe.
    """
    message_lower = message.lower().strip()

    # Confirmações explícitas
    if any(
        word in message_lower
        for word in [
            "sim",
            "ok",
            "correto",
            "certo",
            "perfeito",
            "isso mesmo",
            "confirmo",
        ]
    ):
        return "confirmed"

    # Negações simples - usuário quer alterar mas não especificou o que
    if any(
        word in message_lower
        for word in [
            "não",
            "nao",
            "quero mudar",
            "quero alterar",
            "preciso alterar",
            "mudar",
        ]
    ) and not _has_specific_data(message_lower):
        return "simple_rejection"

    # Possui dados específicos para correção
    if _has_specific_data(message_lower):
        return "correction_with_data"

    return "unclear"


def _has_specific_data(message_lower: str) -> bool:
    """
    Verifica se a mensagem contém dados específicos para correção.
    """
    # Verifica números (horários, datas)
    if any(char.isdigit() for char in message_lower):
        return True

    # Verifica palavras-chave específicas
    specific_keywords = [
        "dr",
        "dra",
        "doutor",
        "doutora",
        "manhã",
        "tarde",
        "noite",
        "segunda",
        "terça",
        "quarta",
        "quinta",
        "sexta",
        "sábado",
        "domingo",
        "cardiologia",
        "pediatria",
        "ortopedia",
        "neurologista",
        "psiquiatra",
        "consulta",
        "retorno",
        "exame",
        "para",
        "com",
        "às",
        "dia",
        "hora",
    ]

    return any(keyword in message_lower for keyword in specific_keywords)


def _handle_confirmed_appointment(state: MessageAgentState) -> MessageAgentState:
    """
    Lida com agendamento confirmado.
    """
    logger.info("Agendamento confirmado pelo usuário")

    current_messages = state.get("messages", [])

    try:
        llm_service = LLMFactory.create_llm_service("openai")
        success_message = llm_service.generate_success_message()
    except Exception as e:
        logger.error(f"Erro ao gerar mensagem de sucesso via IA: {e}")
        success_message = "Dados confirmados com sucesso!"

    updated_messages = current_messages + [AIMessage(content=success_message)]

    return {**state, "messages": updated_messages, "next_step": "appointment_confirmed"}


def _handle_unclear_response(state: MessageAgentState) -> MessageAgentState:
    """
    Lida com resposta não clara do usuário.
    """
    logger.info("Resposta do usuário não foi clara")

    current_messages = state.get("messages", [])

    try:
        llm_service = LLMFactory.create_llm_service("openai")
        clarification_message = llm_service.generate_unclear_response_message()
    except Exception as e:
        logger.error(f"Erro ao gerar mensagem de esclarecimento via IA: {e}")
        clarification_message = "Confirma os dados? Responda 'sim' ou 'não'."

    updated_messages = current_messages + [AIMessage(content=clarification_message)]

    return {
        **state,
        "messages": updated_messages,
        "next_step": "awaiting_final_confirmation",
    }


def _handle_simple_rejection(state: MessageAgentState) -> MessageAgentState:
    """
    Usuário quer alterar mas não especificou dados completos da alteração.
    Pergunta de forma direcionada se o campo for identificado, senão genericamente.
    """
    logger.info("Usuário quer alterar. Verificando se especificou o campo.")

    current_messages = state.get("messages", [])
    last_user_message_content = _get_last_user_message(current_messages)

    correction_message_text = ""
    target_field = _identify_target_field_from_rejection(last_user_message_content)

    if target_field == "horário":
        correction_message_text = "Entendi que você gostaria de alterar o horário. Qual o novo horário de sua preferência (manhã ou tarde, ou o horário específico)?"
    elif target_field == "data":
        correction_message_text = "Certo. Para qual nova data você gostaria de agendar?"
    elif target_field == "profissional":
        correction_message_text = (
            "Ok. Qual o nome do novo profissional que você gostaria de consultar?"
        )
    elif target_field == "especialidade":
        correction_message_text = (
            "Entendido. Qual a nova especialidade que você procura?"
        )
    else:
        logger.info(
            f"Campo específico para correção não identificado em '{last_user_message_content}'. Usando pergunta genérica."
        )
        try:
            llm_service = LLMFactory.create_llm_service("openai")
            correction_message_text = llm_service.generate_correction_request_message()
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de correção genérica via IA: {e}")
            correction_message_text = "Entendi que você quer alterar algo. Por favor, me informe especificamente o que gostaria de mudar (por exemplo, data, horário, profissional ou especialidade)."

    updated_messages = current_messages + [AIMessage(content=correction_message_text)]

    return {**state, "messages": updated_messages, "next_step": "awaiting_correction"}


def _handle_correction_with_data(state: MessageAgentState) -> MessageAgentState:
    """
    Usuário já forneceu dados para correção - processa diretamente.
    """
    logger.info(
        "Usuário forneceu dados de correção diretamente - processando via scheduling_info"
    )

    return {
        **state,
        "next_step": "scheduling_info",
        "conversation_context": "correcting_data",
    }


def _identify_target_field_from_rejection(message: str) -> Optional[str]:
    """
    Identifica o campo alvo que o usuário deseja corrigir a partir de sua mensagem.
    Retorna: "horário", "data", "profissional", "especialidade" ou None.
    """
    if not message:
        return None
    message_lower = message.lower().strip()

    # Dicionário de palavras-chave para cada campo
    keywords_map = {
        "horário": ["horario", "hora", "horas", "turno"],
        "data": ["data", "dia"],
        "profissional": [
            "médico",
            "medico",
            "profissional",
            "doutor",
            "doutora",
            "dr",
            "dra",
        ],
        "especialidade": ["especialidade"],
    }

    for field, field_keywords in keywords_map.items():
        if any(keyword in message_lower for keyword in field_keywords):
            return field  # Retorna o nome do campo se encontrar uma palavra-chave

    return None
