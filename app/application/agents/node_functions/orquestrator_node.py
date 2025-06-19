import logging
import re
from typing import List

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
    logger.info("--- Executando nó orquestrador ---")

    # Extrair informações do estado
    messages = state.get("messages", [])
    if not messages:
        logger.warning("Nenhuma mensagem encontrada no estado.")
        return {**state, "next_step": "fallback_node"}

    # Obter a última mensagem humana
    last_human_message_content = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message_content = msg.content.lower().strip()
            break

    logger.info(f"Orquestrador classificando mensagem: '{last_human_message_content}'")

    # 🆕 NOVA DETECÇÃO: "Não sei" após lista de profissionais
    # Verificar se o bot mostrou lista de profissionais nas últimas 2 mensagens
    recent_ai_messages = [msg.content.lower() for msg in messages[-2:] if 'AI' in str(type(msg))]
    showed_professional_list = any(
        ("encontrei os seguintes profissionais" in msg or 
         "para a especialidade" in msg or
         "gostaria de agendar com algum deles" in msg)
        for msg in recent_ai_messages
    )
    
    # Detectar expressões de incerteza
    uncertainty_phrases = [
        "não sei", "nao sei", "naõ sei",
        "não tenho certeza", "nao tenho certeza", 
        "qualquer um", "tanto faz", "qualquer",
        "não conheço", "nao conheço", "não conheco",
        "você decide", "voce decide",
        "o que você recomenda", "o que voce recomenda",
        "não faço ideia", "nao faco ideia"
    ]
    
    user_expressed_uncertainty = any(phrase in last_human_message_content for phrase in uncertainty_phrases)
    
    # 🆕 RESPOSTA ESPECÍFICA: Quando usuário diz "não sei" após ver lista de profissionais
    if showed_professional_list and user_expressed_uncertainty:
        logger.info(f"🎯 DETECTADO: Usuário expressa incerteza '{last_human_message_content}' após ver lista de profissionais")
        
        # Buscar qual especialidade foi mostrada no contexto
        extracted_details = state.get("extracted_scheduling_details")
        specialty_name = extracted_details.specialty if extracted_details else "dessa especialidade"
        
        gentle_response = (
            f"Entendo! No momento, esses são os únicos profissionais de {specialty_name} "
            f"que temos disponíveis na clínica.\n\n"
            f"Você pode escolher qualquer um deles - todos são excelentes profissionais. "
            f"Ou, se preferir, posso verificar outra especialidade para você.\n\n"
            f"O que você gostaria de fazer?"
        )
        
        from langchain_core.messages import AIMessage
        return {
            **state,
            "messages": messages + [AIMessage(content=gentle_response)],
            "next_step": "completed",
            "conversation_context": "professional_guidance_given",
        }

    # Preparar histórico de conversa
    conversation_history_str = _format_conversation_history_for_prompt(messages)
    
    # Inicializar serviço LLM
    llm_service = LLMFactory.create_llm_service("openai")
    
    # 🔍 DEBUG CRÍTICO: Verificar estado completo
    conversation_context = state.get("conversation_context")
    logger.info(f"🔍 DEBUG - conversation_context recuperado: '{conversation_context}'")
    logger.info(f"🔍 DEBUG - Todas as chaves do estado: {list(state.keys())}")
    
    # 🚨 CORREÇÃO CRÍTICA: Detectar seleção de horário por contexto das mensagens
    # Se não há contexto salvo, mas detectamos padrão de seleção de horário
    if not conversation_context or conversation_context != "awaiting_slot_selection":
        
        # Verificar últimas 2 mensagens para detectar padrão
        if len(messages) >= 2:
            last_ai_message = None
            last_human_message = None
            
            # Buscar última mensagem do assistente e última do usuário
            for msg in reversed(messages):
                if hasattr(msg, 'content') and msg.content:
                    if 'AI' in str(type(msg)) and not last_ai_message:
                        last_ai_message = msg.content.lower()
                    elif 'Human' in str(type(msg)) and not last_human_message:
                        last_human_message = msg.content.lower()
                if last_ai_message and last_human_message:
                    break
            
            logger.info(f"🔍 DEBUG - Última mensagem AI: '{last_ai_message[:100] if last_ai_message else None}...'")
            logger.info(f"🔍 DEBUG - Última mensagem Human: '{last_human_message}'")
            
            # Detectar se estamos em seleção de horário
            if (last_ai_message and last_human_message and 
                ("horários" in last_ai_message or "prefere?" in last_ai_message or 
                 "qual você prefere" in last_ai_message or "encontrei os seguintes" in last_ai_message) and
                (re.search(r'\b\d{1,2}:\d{2}\b', last_human_message) or 
                 re.search(r'\b\d{1,2}\s*e\s*\d{2}\b', last_human_message) or
                 any(time in last_human_message for time in ["8:30", "8 e 30", "08:30", "as 8", "9:30", "7:30"]))):
                
                logger.info("🔥 DETECÇÃO FORÇADA: Contexto de seleção de horário identificado!")
                conversation_context = "awaiting_slot_selection"

    # 🔥 PRIORIDADE ABSOLUTA: Se está aguardando seleção de horário, ir para agendamento
    if conversation_context == "awaiting_slot_selection":
        logger.info("🔥 PRIORIDADE ABSOLUTA: Contexto 'awaiting_slot_selection' - Indo para agendamento!")
        
        # Extrair informações existentes
        existing_details = state.get("extracted_scheduling_details")
        
        # Extrair detalhes atualizados (incluindo specific_time)
        new_details = llm_service.extract_scheduling_details(conversation_history_str)
        updated_details = _merge_scheduling_details(existing_details, new_details)
        
        logger.info(f"📋 Detalhes para agendamento: {updated_details}")
        
        return {
            **state,
            "extracted_scheduling_details": updated_details,
            "next_step": "book_appointment_node",
            "conversation_context": "completing_appointment",
        }

    # 🆕 DETECÇÃO INTELIGENTE: Nome de profissional após listagem
    # Verificar se o bot mostrou lista de profissionais recentemente
    recent_ai_messages = [msg.content.lower() for msg in messages[-3:] if 'AI' in str(type(msg))]
    showed_professional_list = any(
        ("clara joaquina" in msg or "joão josé" in msg or "encontrei os seguintes profissionais" in msg)
        for msg in recent_ai_messages
    )

    # Se mostrou lista e usuário respondeu com nome simples, tratar como scheduling_info
    simple_name_responses = ["clara", "joão", "silva", "maria", "ana", "carlos"]
    if (showed_professional_list and 
        last_human_message_content.strip().lower() in simple_name_responses):
        
        logger.info(f"🎯 DETECÇÃO INTELIGENTE: Nome '{last_human_message_content}' após listagem - Forçando scheduling_info")
        classification = "scheduling_info"

    # 🧠 CLASSIFICAÇÃO INTELIGENTE COM CONTEXTO
    # Obter últimas mensagens para contexto
    recent_messages = messages[-6:] if len(messages) >= 6 else messages[:-1]
    
    # Formatar contexto da conversa
    conversation_context = ""
    if recent_messages:
        context_parts = []
        for msg in recent_messages:
            if hasattr(msg, 'content'):
                speaker = "Sistema" if 'AI' in str(type(msg)) else "Usuário"
                context_parts.append(f"{speaker}: {msg.content}")
        conversation_context = "\n".join(context_parts)
    
    logger.info(f"🧠 Contexto para classificação:\n{conversation_context}")
    
    # Classificar mensagem usando contexto inteligente
    classification = llm_service.classify_message_with_context(
        message=last_human_message_content,
        context=conversation_context
    )
    logger.info(f"🎯 Classificação inteligente: '{classification}'")

    # Extrair detalhes existentes do estado
    existing_details = state.get("extracted_scheduling_details")
    existing_missing_fields = state.get("missing_fields", [])
    existing_context = state.get("conversation_context")

    # Verificar se é uma query de API
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
    
    # ✅ CORREÇÃO CRÍTICA: Verificar se estamos no meio de um fluxo de agendamento ANTES da classificação
    # Se tem detalhes existentes, campos faltantes ou contexto de agendamento, manter o fluxo
    if (
        existing_details
        or existing_missing_fields
        or existing_context == "scheduling_flow"
    ):
        logger.info(
            f"🔄 MANTENDO CONTEXTO DE AGENDAMENTO - Classificação: '{classification}', mas continuando fluxo"
        )
        
        # ✅ DETECÇÃO ESPECÍFICA: Resposta de turno (manha/tarde) quando há campos faltantes
        if (
            existing_missing_fields
            and any("turno" in field for field in existing_missing_fields)
            and last_human_message_content.strip().lower() in ["manha", "manhã", "tarde"]
        ):
            logger.info(
                f"🎯 PRIORIDADE ABSOLUTA: Usuário respondeu turno '{last_human_message_content}' - Forçando scheduling_info"
            )
            # Extrair dados forçadamente
            new_details = llm_service.extract_scheduling_details(conversation_history_str)
            updated_details = _merge_scheduling_details(existing_details, new_details)
            
            return {
                **state,
                "extracted_scheduling_details": updated_details,
                "next_step": "scheduling_info",
                "conversation_context": "scheduling_flow",
            }
        
        # Sempre extrair dados se estamos no contexto de agendamento
        new_details = llm_service.extract_scheduling_details(conversation_history_str)
        updated_details = _merge_scheduling_details(existing_details, new_details)
        state["extracted_scheduling_details"] = updated_details
        logger.info(f"Dados de agendamento atualizados: {updated_details}")

        # Continuar com lógica de agendamento...

    # Se está aguardando nova data, continuar no fluxo
    elif conversation_context == "awaiting_new_date_selection":
        logger.info(
            f"🔥 PRIORIDADE ABSOLUTA: Contexto 'awaiting_new_date_selection' - Mantendo fluxo"
        )
        new_details = llm_service.extract_scheduling_details(conversation_history_str)
        updated_details = _merge_scheduling_details(existing_details, new_details)

        return {
            **state,
            "extracted_scheduling_details": updated_details,
            "next_step": "scheduling_info",
            "conversation_context": "scheduling_flow",
        }

    # Se NÃO estiver no contexto de agendamento E a classificação não for sobre agendamento
    elif classification not in ["scheduling", "scheduling_info"]:
        return {
            **state,
            "next_step": classification,
            "conversation_context": classification,
        }
    else:
        # APENAS se for sobre agendamento E não estamos em contexto, extrair dados
        new_details = llm_service.extract_scheduling_details(conversation_history_str)
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
                "Usuário perguntou sobre disponibilidade mas não definiu especialidade. Direcionando para esclarecimento."
            )
            return {
                **state,
                "next_step": "clarification",
                "missing_fields": ["especialidade"],
            }

    # TERCEIRA PRIORIDADE: Calcular campos faltantes com nova prioridade
    calculated_missing_fields = []
    if updated_details:
        # ✅ CORREÇÃO: Só pedir especialidade se NÃO tiver
        if not updated_details.specialty:
            calculated_missing_fields.append("especialidade")
        # ✅ CORREÇÃO: Só verificar outros campos se JÁ tem especialidade
        else:  # Se JÁ tem especialidade, verificar outros campos
            if updated_details.specialty and not updated_details.professional_name:
                # Se tem especialidade mas não tem profissional: mostrar profissionais automaticamente
                logger.info(f"🎯 TEM ESPECIALIDADE '{updated_details.specialty}' - Direcionando para seleção de profissionais")
                return {
                    **state,
                    "next_step": AGENT_TOOL_CALLER_NODE_NAME,
                    "conversation_context": "specialty_selection",
                }
                
            if not updated_details.date_preference:
                calculated_missing_fields.append("data de preferência")
            if not updated_details.time_preference:
                calculated_missing_fields.append("turno de preferência")

    # 🔧 CORREÇÃO CRÍTICA: Se extraiu informações de agendamento e faltam campos críticos
    if updated_details and calculated_missing_fields:
        logger.info(
            f"Agendamento detectado com campos faltando: {calculated_missing_fields}."
        )
        
        # 🔧 NOVA LÓGICA: Se já está no contexto de agendamento, usar scheduling_info
        current_context = state.get("conversation_context", "")
        if current_context == "scheduling_flow":
            logger.info("✅ JÁ no contexto de agendamento - direcionando para scheduling_info_node")
            return {
                **state,
                "missing_fields": calculated_missing_fields,
                "next_step": "scheduling_info",
                "conversation_context": "scheduling_flow",
            }
        else:
            logger.info("🆕 Primeira vez no agendamento - direcionando para clarification")
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
            "conversation_context": "scheduling_flow",
        }

    # Funcionalidade de roteamento com base em contexto
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


def _format_conversation_history_for_prompt(
    messages: list[BaseMessage], max_messages: int = 10
) -> str:
    """Formata o histórico da conversa para uso em prompts."""
    recent_messages = messages[-max_messages:]
    formatted = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            formatted.append(f"Usuário: {msg.content}")
        else:  # AIMessage
            formatted.append(f"Assistente: {msg.content}")
    return "\n".join(formatted)


def _merge_scheduling_details(
    existing: SchedulingDetails, new: SchedulingDetails
) -> SchedulingDetails:
    """Mescla detalhes de agendamento, priorizando novos valores não-nulos."""
    if not existing:
        return new if new else SchedulingDetails()
    if not new:
        return existing

    return SchedulingDetails(
        professional_name=new.professional_name or existing.professional_name,
        specialty=new.specialty or existing.specialty,
        date_preference=new.date_preference or existing.date_preference,
        time_preference=new.time_preference or existing.time_preference,
        specific_time=new.specific_time or existing.specific_time,
        service_type=new.service_type or existing.service_type or "consulta",
    )
