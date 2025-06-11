import logging

from langchain_core.messages import BaseMessage, HumanMessage

from app.application.agents.state.message_agent_state import MessageAgentState
from app.domain.sheduling_details import SchedulingDetails
from app.infrastructure.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

AGENT_TOOL_CALLER_NODE_NAME = "agent_tool_caller"


def orquestrator_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó orquestrador que classifica a intenção do usuário e define o próximo passo.
    """
    logger.info(f"--- Executando nó orquestrador ---")

    messages = state.get("messages", [])
    conversation_history_str = _format_conversation_history_for_prompt(messages)
    existing_details = state.get("extracted_scheduling_details")
    existing_missing_fields = state.get("missing_fields", [])
    existing_context = state.get("conversation_context")

    # PRIMEIRO: Classificar a intenção
    last_human_message_content = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message_content = msg.content
            break

    if not last_human_message_content:
        logger.warning(
            "Nenhuma mensagem humana encontrada no estado para o orquestrador."
        )
        return {**state, "next_step": "unclear", "conversation_context": "system_error"}

    logger.info(f"Orquestrador classificando mensagem: '{last_human_message_content}'")

    try:
        llm_service = LLMFactory.create_llm_service("openai")
        classification = llm_service.classify_message(last_human_message_content)
        classification = classification.strip().lower()
        logger.info(f"Classificação: '{classification}'")

        # 🆕 PRIORIDADE MÁXIMA: Queries de API sempre têm precedência
        if classification in ["api_query", "specialty_selection"]:
            logger.info(
                f"🎯 QUERY DE API detectada: '{classification}' - Direcionando para tool"
            )
            return {
                **state,
                "next_step": AGENT_TOOL_CALLER_NODE_NAME,
                "conversation_context": classification,
            }

        # 🔥 NOVA PRIORIDADE CRÍTICA: Verificar contextos específicos de agendamento PRIMEIRO
        conversation_context = state.get("conversation_context")

        # Se está aguardando seleção de horário, SEMPRE continuar no fluxo, independente da classificação
        if conversation_context == "awaiting_slot_selection":
            logger.info(
                f"🔥 PRIORIDADE ABSOLUTA: Contexto 'awaiting_slot_selection' - Mantendo fluxo independente da classificação '{classification}'"
            )
            # Extrair detalhes atualizados (incluindo "manha"/"tarde")
            new_details = llm_service.extract_scheduling_details(
                conversation_history_str
            )
            updated_details = _merge_scheduling_details(existing_details, new_details)

            return {
                **state,
                "extracted_scheduling_details": updated_details,
                "next_step": "book_appointment_node",
                "conversation_context": conversation_context,  # Manter contexto
            }

        # Se está aguardando nova data, continuar no fluxo
        if conversation_context == "awaiting_new_date_selection":
            logger.info(
                f"🔥 PRIORIDADE ABSOLUTA: Contexto 'awaiting_new_date_selection' - Mantendo fluxo"
            )
            new_details = llm_service.extract_scheduling_details(
                conversation_history_str
            )
            updated_details = _merge_scheduling_details(existing_details, new_details)

            return {
                **state,
                "extracted_scheduling_details": updated_details,
                "next_step": "scheduling_info",
                "conversation_context": "scheduling_flow",
            }

        # APENAS DEPOIS verificar contexto de agendamento geral
        if (
            existing_details
            or existing_missing_fields
            or existing_context == "scheduling_flow"
        ):
            logger.info(
                f"🔄 MANTENDO CONTEXTO DE AGENDAMENTO - Classificação: '{classification}', mas continuando fluxo"
            )
            # Sempre extrair dados se estamos no contexto de agendamento
            new_details = llm_service.extract_scheduling_details(
                conversation_history_str
            )
            updated_details = _merge_scheduling_details(existing_details, new_details)
            state["extracted_scheduling_details"] = updated_details
            logger.info(f"Dados de agendamento atualizados: {updated_details}")

            # Continuar com lógica de agendamento...
        # Se NÃO estiver no contexto de agendamento E a classificação não for sobre agendamento
        elif classification not in ["scheduling", "scheduling_info"]:
            return {
                **state,
                "next_step": classification,
                "conversation_context": classification,
            }
        else:
            # APENAS se for sobre agendamento E não estamos em contexto, extrair dados
            new_details = llm_service.extract_scheduling_details(
                conversation_history_str
            )
            updated_details = _merge_scheduling_details(existing_details, new_details)
            state["extracted_scheduling_details"] = updated_details
            logger.info(f"Dados de agendamento extraídos: {updated_details}")

        # Continuar com a lógica de agendamento...
        # PRIMEIRA PRIORIDADE: Detectar menção de especialidade e ser proativo
        last_message = messages[-1].content.lower().strip() if messages else ""

        # NOVA PRIORIDADE MÁXIMA: Detectar perguntas sobre informações da clínica
        # Estas perguntas devem ter prioridade sobre qualquer fluxo de agendamento
        clinic_info_keywords = [
            "quais especialidades",
            "que especialidades",
            "especialidades disponíveis",
            "especialidades que vocês têm",
            "especialidades da clínica",
            "quais médicos",
            "que médicos",
            "médicos disponíveis",
            "profissionais disponíveis",
            "quais profissionais",
            "que profissionais",
        ]

        if any(keyword in last_message for keyword in clinic_info_keywords):
            logger.info(
                f"🔍 PRIORIDADE MÁXIMA: Usuário está perguntando sobre informações da clínica: '{last_message}'"
            )
            return {
                **state,
                "next_step": AGENT_TOOL_CALLER_NODE_NAME,
                "conversation_context": "api_query",
            }

        # Lista expandida de especialidades e suas variações
        specialty_keywords = [
            "cardiologia",
            "cardiologista",
            "cardio",
            "pediatria",
            "pediatra",
            "pedra",
            "ortopedia",
            "ortopedista",
            "orto",
            "clínico geral",
            "clinico geral",
            "clínico",
            "clinico",
            "ginecologia",
            "ginecologista",
            "gineco",
            "dermatologia",
            "dermatologista",
            "dermato",
            "neurologia",
            "neurologista",
            "neuro",
            "psiquiatria",
            "psiquiatra",
        ]

        # Se o usuário mencionou uma especialidade E o sistema extraiu uma especialidade, ser proativo
        if (
            updated_details
            and updated_details.specialty
            and not updated_details.professional_name
            and any(keyword in last_message for keyword in specialty_keywords)
        ):
            logger.info(
                f"🎯 DETECTADO: Usuário mencionou especialidade '{last_message}' -> Extraído: '{updated_details.specialty}'. Sendo proativo!"
            )
            return {
                **state,
                "next_step": AGENT_TOOL_CALLER_NODE_NAME,
                "conversation_context": "specialty_selection",
            }

        # SEGUNDA PRIORIDADE: Verificar disponibilidade
        if any(
            keyword in last_message
            for keyword in [
                "disponível",
                "datas",
                "horários",
                "agenda",
                "disponibilidade",
                "livre",
                "vago",
                "quando",
            ]
        ):
            if updated_details and updated_details.professional_name:
                logger.info(
                    f"Usuário perguntou sobre disponibilidade para '{updated_details.professional_name}'. Direcionando para tool."
                )
                return {
                    **state,
                    "next_step": AGENT_TOOL_CALLER_NODE_NAME,
                    "conversation_context": "checking_availability",
                }
            else:
                logger.info(
                    "Usuário perguntou sobre disponibilidade mas não definiu profissional. Direcionando para esclarecimento."
                )
                return {
                    **state,
                    "next_step": "clarification",
                    "missing_fields": ["nome do profissional"],
                }

        # TERCEIRA PRIORIDADE: Calcular campos faltantes apenas se não detectou especialidade
        calculated_missing_fields = []
        if updated_details:
            if not updated_details.professional_name and not updated_details.specialty:
                calculated_missing_fields.append("nome do profissional ou especialidade")
            elif not updated_details.professional_name and updated_details.specialty:
                # Se tem especialidade mas não tem profissional, NÃO adiciona aos campos faltantes
                # porque vamos buscar os profissionais automaticamente
                pass
            if not updated_details.date_preference:
                calculated_missing_fields.append("data de preferência")
            if not updated_details.time_preference:
                calculated_missing_fields.append("turno de preferência")

        # Se extraiu informações de agendamento e faltam campos críticos, vai para clarification
        if updated_details and calculated_missing_fields:
            logger.info(
                f"Agendamento detectado com campos faltando: {calculated_missing_fields}. Direcionando para clarification."
            )
            return {
                **state,
                "missing_fields": calculated_missing_fields,
                "next_step": "clarification",
                "conversation_context": "scheduling_flow",
            }

        current_next_step = state.get("next_step", "")
        if current_next_step == "awaiting_final_confirmation":
            logger.info("Estado indica que estamos aguardando confirmação final")
            return {**state, "next_step": "final_confirmation"}

        if current_next_step == "awaiting_correction":
            logger.info(
                "Estado indica que estamos aguardando correção - direcionando para scheduling_info"
            )
            return {
                **state,
                "next_step": "scheduling_info",
                "conversation_context": "correcting_data",
            }

        conversation_context = state.get("conversation_context")

        # Se o usuário está selecionando um HORÁRIO, vá para o agendamento final.
        if conversation_context == "awaiting_slot_selection":
            logger.info(
                f"Contexto é '{conversation_context}', direcionando para o agendamento final."
            )
            return {**state, "next_step": "book_appointment_node"}

        # Se o usuário está selecionando uma nova DATA, volte para a coleta de informações.
        if conversation_context == "awaiting_new_date_selection":
            logger.info(
                f"Contexto é '{conversation_context}', direcionando para a coleta de informações (scheduling_info)."
            )
            return {**state, "next_step": "scheduling_info"}

        # NOVA LÓGICA: Verificar se estamos no meio de um fluxo de agendamento
        missing_fields = state.get("missing_fields", [])

        # CORRIGIDO: usar updated_details em vez de extracted_details
        if updated_details and missing_fields:
            logger.info(
                f"Contexto de agendamento detectado com campos faltando: {missing_fields}. "
                "Tratando resposta como scheduling_info."
            )
            return {
                **state,
                "next_step": "scheduling_info",
                "conversation_context": "scheduling_flow",
            }

        next_step_map = {
            "scheduling": "scheduling",
            "scheduling_info": "scheduling_info",
            "greeting": "greeting",
            "farewell": "farewell",
            "api_query": AGENT_TOOL_CALLER_NODE_NAME,
            "specialty_selection": AGENT_TOOL_CALLER_NODE_NAME,
            "other": "other",
            "unclear": "fallback_node",
        }

        next_node = next_step_map.get(classification, "fallback_node")

        new_conversation_context = classification
        if classification in ["scheduling", "scheduling_info"]:
            new_conversation_context = "scheduling_flow"
        elif classification in ["api_query", "specialty_selection"]:
            new_conversation_context = "api_interaction"

        logger.info(
            f"Orquestrador definiu next_step para: '{next_node}' com contexto: '{new_conversation_context}'"
        )
        return {
            **state,
            "next_step": next_node,
            "conversation_context": new_conversation_context,
        }

    except Exception as e:
        logger.error(f"Erro no orquestrador: {e}")
        return {**state, "next_step": "fallback_node"}


def _format_conversation_history_for_prompt(
    messages: list[BaseMessage], max_messages: int = 10
) -> str:
    if not messages:
        return "Nenhuma conversa ainda"
    recent_messages = messages[-max_messages:]
    formatted_history = []
    for msg in recent_messages:
        role = "Usuário" if isinstance(msg, HumanMessage) else "Assistente"
        formatted_history.append(f"{role}: {msg.content}")
    return "\n".join(formatted_history)


def _merge_scheduling_details(
    existing: SchedulingDetails, new: SchedulingDetails
) -> SchedulingDetails:
    if not existing:
        return new
    if not new:
        return existing

    # Lógica de mesclagem: O novo valor (extraído da conversa mais recente) tem prioridade.
    merged = SchedulingDetails(
        professional_name=new.professional_name or existing.professional_name,
        specialty=new.specialty or existing.specialty,
        date_preference=new.date_preference or existing.date_preference,
        time_preference=new.time_preference or existing.time_preference,
        specific_time=new.specific_time or existing.specific_time,
        service_type=new.service_type or existing.service_type,
    )
    return merged
