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
    Nó responsável pela orquestração inteligente das mensagens do usuário.
    """

    logger.info("--- Executando nó orquestrador ---")
    llm_service = LLMFactory.create_llm_service("openai")

    messages: List[BaseMessage] = state.get("messages", [])
    existing_details = state.get("extracted_scheduling_details")
    conversation_context = state.get("conversation_context", "")

    if not messages:
        logger.error("Nenhuma mensagem encontrada no estado")
        return {**state, "next_step": "fallback_node"}

    # Obter o conteúdo da última mensagem humana
    last_human_message_content = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message_content = msg.content
            break

    if not last_human_message_content:
        logger.error("Nenhuma mensagem humana encontrada")
        return {**state, "next_step": "fallback_node"}

    logger.info(f"Orquestrador classificando mensagem: '{last_human_message_content}'")

    # Debugs para entender o estado
    logger.info(f"🔍 DEBUG - conversation_context recuperado: '{conversation_context}'")
    logger.info(f"🔍 DEBUG - Todas as chaves do estado: {list(state.keys())}")

    # Debug das últimas mensagens
    ai_messages = [msg for msg in messages if hasattr(msg, 'type') and msg.type == 'ai']
    human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    
    if ai_messages:
        last_ai_content = ai_messages[-1].content[:100] + "..." if len(ai_messages[-1].content) > 100 else ai_messages[-1].content
        logger.info(f"🔍 DEBUG - Última mensagem AI: '{last_ai_content.lower()}'")
    
    if human_messages:
        logger.info(f"🔍 DEBUG - Última mensagem Human: '{human_messages[-1].content}'")

    # Criar contexto para classificação
    conversation_history_str = _format_conversation_history_for_prompt(messages, max_messages=4)
    logger.info(f"🧠 Contexto para classificação:\n{conversation_history_str}")

    # 🔧 NOVA CORREÇÃO: Detectar respostas afirmativas para alternar turno
    # ANTES da classificação inteligente
    
    # Verificar se estamos em contexto de pergunta sobre alternar turno
    missing_fields = state.get("missing_fields", [])
    is_asking_time_preference = "turno de preferência" in missing_fields
    
    # Detectar se a última mensagem AI perguntou sobre outro turno
    last_ai_message = ""
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'ai':
            last_ai_message = msg.content.lower()
            break
    
    asked_about_other_shift = any(phrase in last_ai_message for phrase in [
        "gostaria de tentar outro turno",
        "quer outro turno", 
        "outro período",
        "outro horário", 
        "tentar outro turno"
    ])
    
    # 🔧 CONDIÇÃO CRÍTICA: Se perguntou sobre alternar turno E usuário deu resposta afirmativa
    if (is_asking_time_preference or asked_about_other_shift) and existing_details:
        affirmative_responses = [
            "quero", "sim", "ok", "pode ser", "tudo bem", "ta bom", "tá bom",
            "perfeito", "beleza", "claro", "certeza", "vamos", "aceito",
            "concordo", "positivo", "yes", "é", "eh", "uhum", "uh-hum",
            "claro", "certo", "correto", "isso", "exato", "perfeito",
            "show", "ótimo", "otimo", "legal", "bacana", "massa",
            "vale", "valeu", "vamos nessa", "por favor", "pfv"
        ]
        
        user_wants_time_shift = any(
            response in last_human_message_content.lower() 
            for response in affirmative_responses
        )
        
        if user_wants_time_shift:
            logger.info(f"🔥 DETECTADO ALTERNAR TURNO: '{last_human_message_content}' - Alternando automaticamente!")
            
            # Alternar o turno mantendo TODOS os outros dados
            current_time_preference = existing_details.time_preference or "manha"
            new_time_preference = "tarde" if current_time_preference == "manha" else "manha"
            
            logger.info(f"🔄 ALTERNANDO: {current_time_preference} → {new_time_preference}")
            
            # 🔧 PRESERVAR ABSOLUTAMENTE TODOS OS DADOS
            updated_details = SchedulingDetails(
                professional_name=existing_details.professional_name,
                specialty=existing_details.specialty,                  
                date_preference=existing_details.date_preference,      
                time_preference=new_time_preference,                   # ✅ SÓ ESTE MUDA
                specific_time=None,                                    # Reset apenas specific_time
                service_type=existing_details.service_type or "consulta",
                patient_name=existing_details.patient_name,           
            )
            
            logger.info(f"✅ Detalhes preservados com novo turno: {updated_details}")
            
            return {
                **state,
                "extracted_scheduling_details": updated_details,
                "next_step": "check_availability_node",
                "conversation_context": "time_shift_completed",  # 🔧 CONTEXTO ESPECÍFICO
                "missing_fields": [],  # 🔧 LIMPAR CAMPOS FALTANTES
            }

    # Classificação inteligente usando LLM
    classification = llm_service.classify_message_with_context(
        message=last_human_message_content,
        context=conversation_history_str,
    )
    logger.info(f"🎯 Classificação inteligente: '{classification}'")

    # CORREÇÃO: Se estamos no contexto de agendamento, manter sempre
    if conversation_context == "scheduling_flow":
        logger.info(f"🔄 MANTENDO CONTEXTO DE AGENDAMENTO - Classificação: '{classification}', mas continuando fluxo")

    # Extrair dados se for relacionado a agendamento
    if classification in ["scheduling", "scheduling_info"] or conversation_context == "scheduling_flow":
        new_details = llm_service.extract_scheduling_details(conversation_history_str)
        updated_details = _merge_scheduling_details(existing_details, new_details)
        state["extracted_scheduling_details"] = updated_details
        logger.info(f"Dados de agendamento atualizados: {updated_details}")

    # 🔧 CORREÇÃO 2: Detectar quando usuário quer alternar turno (contexto específico)
    elif conversation_context == "awaiting_time_shift":
        logger.info(f"🔥 CONTEXTO 'awaiting_time_shift' - Verificando resposta afirmativa")
        
        # Detectar respostas afirmativas
        affirmative_responses = [
            "quero", "sim", "ok", "pode ser", "tudo bem", "ta bom", "tá bom",
            "perfeito", "beleza", "claro", "certeza", "vamos", "aceito",
            "concordo", "positivo", "yes", "é", "eh", "uhum", "uh-hum",
            "claro", "certo", "correto", "isso", "exato", "perfeito",
            "show", "ótimo", "otimo", "legal", "bacana", "massa",
            "vale", "valeu", "vamos nessa", "por favor", "pfv"
        ]
        
        user_wants_time_shift = any(
            response in last_human_message_content.lower() 
            for response in affirmative_responses
        )
        
        if user_wants_time_shift:
            logger.info(f"✅ DETECTADO: Usuário quer alternar turno - '{last_human_message_content}'")
            
            # 🔧 PRESERVAR TODOS OS DADOS EXISTENTES
            if existing_details:
                # Alternar o turno mantendo TODOS os outros dados
                current_time_preference = existing_details.time_preference or "manha"
                new_time_preference = "tarde" if current_time_preference == "manha" else "manha"
                
                logger.info(f"🔄 ALTERNANDO: {current_time_preference} → {new_time_preference}")
                
                # 🔧 PRESERVAR ABSOLUTAMENTE TODOS OS DADOS
                updated_details = SchedulingDetails(
                    professional_name=existing_details.professional_name,  # 🔧 MANTER
                    specialty=existing_details.specialty,                  # 🔧 MANTER  
                    date_preference=existing_details.date_preference,      # 🔧 MANTER
                    time_preference=new_time_preference,                   # 🔧 ALTERNAR APENAS ESTE
                    specific_time=None,                                    # Reset apenas specific_time
                    service_type=existing_details.service_type or "consulta", # 🔧 MANTER
                    patient_name=existing_details.patient_name,           # 🔧 MANTER
                )
                
                logger.info(f"✅ Detalhes preservados com novo turno: {updated_details}")
                
                return {
                    **state,
                    "extracted_scheduling_details": updated_details,
                    "next_step": "check_availability_node",
                    "conversation_context": "time_shift_completed",  # 🔧 NOVO CONTEXTO
                    "missing_fields": [],  # 🔧 LIMPAR CAMPOS FALTANTES
                }
            else:
                logger.warning("⚠️ Não há detalhes existentes para preservar - redirecionando para clarification")
                return {
                    **state,
                    "next_step": "clarification",
                    "conversation_context": "scheduling_flow",
                }
        else:
            # Se não é resposta afirmativa, tratar como resposta negativa
            logger.info(f"❌ Usuário não quer alternar turno - '{last_human_message_content}'")
            return {
                **state,
                "next_step": "clarification",
                "conversation_context": "scheduling_flow",
                "missing_fields": ["turno de preferência"],
            }

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

    # 🔧 CORREÇÃO: Se extraiu informações de agendamento e faltam campos críticos
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
                "conversation_context": "scheduling_flow",  # 🔧 MANTER CONTEXTO
            }
        else:
            logger.info("🆕 Primeira vez no agendamento - direcionando para clarification")
            return {
                **state,
                "missing_fields": calculated_missing_fields,
                "next_step": "clarification", 
                "conversation_context": "scheduling_flow",  # 🔧 DEFINIR CONTEXTO
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
            formatted.append(f"Sistema: {msg.content}")
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
        patient_name=new.patient_name or existing.patient_name,
    )
