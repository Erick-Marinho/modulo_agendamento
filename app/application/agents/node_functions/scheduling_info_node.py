import logging
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage

from app.application.agents.state.message_agent_state import (
    MessageAgentState,
    SchedulingDetails,
)
from app.infrastructure.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


def scheduling_info_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó responsável por processar informações fornecidas pelo usuário durante o agendamento.
    Este nó é chamado quando o usuário está respondendo a perguntas sobre agendamento.
    """

    logger.info("--- Executando nó scheduling_info ---")

    extracted_details = state.get("extracted_scheduling_details")

    if extracted_details is None:
        logger.info("Primeira extração de detalhes de agendamento.")
        return _extract_initial_details(state)

    logger.info("Extração de detalhes de agendamento já realizada.")
    return _update_existing_details(state)


def _extract_initial_details(state: MessageAgentState) -> MessageAgentState:
    """
    Extrai os detalhes iniciais de agendamento do usuário.
    """
    logger.info("Extraindo detalhes iniciais de agendamento.")

    try:
        llm_service = LLMFactory.create_llm_service("openai")

        messages = state.get("messages", [])
        conversation_history = _format_conversation_history(messages)

        logger.info(f"Extraindo detalhes iniciais do histórico: {conversation_history}")

        extracted_data = llm_service.extract_scheduling_details(conversation_history)

        if extracted_data:
            logger.info(f"Detalhes iniciais extraídos: {extracted_data}")
            return {
                **state,
                "extracted_scheduling_details": extracted_data,
                "next_step": "check_completeness",
            }
        else:
            logger.warning("Falha na extração de detalhes de agendamento.")
            return {**state, "next_step": "clarification"}
    except Exception as e:
        logger.error(f"Erro ao extrair detalhes de agendamento: {e}", exc_info=True)
        return {**state, "next_step": "clarification"}


def _update_existing_details(state: MessageAgentState) -> MessageAgentState:
    """
    Atualiza os detalhes de agendamento existentes com as informações fornecidas pelo usuário.
    """
    try:
        conversation_context = state.get("conversation_context", "")

        # 🆕 CASO ESPECIAL: Usuário está escolhendo nova data
        if conversation_context == "awaiting_date_selection":
            logger.info(
                "🔄 Contexto 'awaiting_date_selection' - Processando nova data escolhida"
            )

            # Apenas extrair e atualizar os detalhes - NÃO gerar mensagem
            llm_service = LLMFactory.create_llm_service("openai")
            all_messages = state.get("messages", [])
            conversation_history = _format_conversation_history(
                all_messages, max_messages=3
            )

            new_details = llm_service.extract_scheduling_details(conversation_history)

            if new_details:
                existing_details = state.get("extracted_scheduling_details")
                updated_details = _merge_scheduling_details(
                    existing_details, new_details
                )

                logger.info(f"Nova data extraída: {updated_details.date_preference}")

                return {
                    **state,
                    "extracted_scheduling_details": updated_details,
                    "conversation_context": "",  # Limpar contexto
                    "next_step": "check_availability_node",
                }

            logger.warning("Falha ao extrair nova data")
            return {**state, "next_step": "clarification"}

        # Fluxo normal continua...
        llm_service = LLMFactory.create_llm_service("openai")

        all_messages = state.get("messages", [])
        if not all_messages:
            logger.warning("Nenhuma mensagem encontrada para atualização")
            return {**state, "next_step": "clarification"}

        conversation_history = _format_conversation_history(all_messages, max_messages=3)

        logger.info(
            f"Atualizando detalhes com o histórico recente: '{conversation_history}'"
        )

        new_details = llm_service.extract_scheduling_details(conversation_history)

        if new_details:
            existing_details = state.get("extracted_scheduling_details")
            updated_details = _merge_scheduling_details(existing_details, new_details)

            logger.info(f"Detalhes atualizados: {updated_details}")

            # --- LÓGICA DE DIRECIONAMENTO ---
            if conversation_context == "awaiting_new_date_selection":
                next_node = "check_availability_node"
                logger.info(
                    "Redirecionando de volta para a verificação de disponibilidade."
                )
            else:
                # Comportamento padrão: verificar se os dados estão completos.
                next_node = "check_completeness"

            return {
                **state,
                "extracted_scheduling_details": updated_details,
                "next_step": next_node,
            }
        else:
            logger.warning(
                "Nenhum detalhe novo extraído da mensagem. Verifique o prompt de extração e o contexto."
            )
            return {**state, "next_step": "check_completeness"}

    except Exception as e:
        logger.error(f"Erro ao atualizar detalhes: {e}")
        return {**state, "next_step": "clarification"}


def _format_conversation_history(messages, max_messages: int = 5) -> str:
    """
    Formata o histórico de conversa para envio ao LLM.
    """
    if not messages:
        return "Nenhuma conversa ainda"

    recent_messages = messages[-max_messages:]
    formatted_history = []

    for msg in recent_messages:
        role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
        formatted_history.append(f"{role}: {msg.content}")

    return "\n".join(formatted_history)


def _merge_scheduling_details(existing, new):
    """
    Mescla detalhes de agendamento, priorizando informações mais recentes.
    """
    if not existing:
        logger.info("Nenhum detalhe existente, retornando dados novos")
        return new

    if not new:
        logger.info("Nenhum detalhe novo, retornando dados existentes")
        return existing

    merged = SchedulingDetails(
        professional_name=existing.professional_name or new.professional_name,
        specialty=existing.specialty or new.specialty,
        date_preference=existing.date_preference or new.date_preference,
        time_preference=existing.time_preference or new.time_preference,
        service_type=existing.service_type or new.service_type,
    )

    return merged
