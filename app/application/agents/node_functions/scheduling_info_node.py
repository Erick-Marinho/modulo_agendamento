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

    # 🆕 DETECÇÃO ESPECÍFICA MELHORADA: Perguntas sobre especialidades/profissionais
    messages = state.get("messages", [])
    last_message = messages[-1].content.lower().strip() if messages else ""

    # 🆕 NOVA DETECÇÃO CRÍTICA: Expressões de "data mais próxima"
    proximity_phrases = [
        "mais próxima", "mais proxima", "a mais próxima", "a mais proxima",
        "primeira disponível", "primeira data", "qualquer data",
        "quanto antes", "o mais breve", "breve possível",
        "próxima data", "proxima data", "primeira vaga"
    ]
    
    user_wants_earliest = any(phrase in last_message for phrase in proximity_phrases)
    
    # 🔧 TRATAMENTO ESPECÍFICO: Data mais próxima (PRIORIDADE MÁXIMA)
    if user_wants_earliest:
        logger.info(f"🎯 DETECTADO: Usuário quer data mais próxima: '{last_message}'")
        
        extracted_details = state.get("extracted_scheduling_details")
        if not extracted_details:
            logger.info("Primeira extração com data mais próxima")
            return _extract_initial_details(state)
        
        # Atualizar forçadamente com a preferência de "data mais próxima"
        updated_details = SchedulingDetails(
            professional_name=extracted_details.professional_name,
            specialty=extracted_details.specialty,
            date_preference="a mais próxima",  # 🔧 FORÇAR valor específico
            time_preference=extracted_details.time_preference,
            specific_time=extracted_details.specific_time,
            service_type=extracted_details.service_type or "consulta",
        )
        
        logger.info(f"✅ Data mais próxima aplicada manualmente: {updated_details}")
        
        return {
            **state,
            "extracted_scheduling_details": updated_details,
            "next_step": "check_completeness",
            "conversation_context": "scheduling_flow",
        }

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
    
    user_expressed_uncertainty = any(phrase in last_message for phrase in uncertainty_phrases)
    
    # 🆕 RESPOSTA ESPECÍFICA: Quando usuário diz "não sei" após ver lista de profissionais
    if showed_professional_list and user_expressed_uncertainty:
        logger.info(f"🎯 DETECTADO: Usuário expressa incerteza '{last_message}' após ver lista de profissionais")
        
        # Buscar qual especialidade foi mostrada no contexto
        extracted_details = state.get("extracted_scheduling_details")
        specialty_name = extracted_details.specialty if extracted_details else "dessa especialidade"
        
        gentle_response = (
            f"Sem problemas! No momento, esses são os únicos profissionais de {specialty_name} "
            f"que temos disponíveis na clínica.\n\n"
            f"Todos são excelentes profissionais e você pode escolher qualquer um deles. "
            f"Ou, se preferir, posso mostrar profissionais de outra especialidade.\n\n"
            f"O que você prefere?"
        )
        
        return {
            **state,
            "messages": messages + [AIMessage(content=gentle_response)],
            "next_step": "completed",
            "conversation_context": "awaiting_professional_choice",
        }

    # Palavras-chave expandidas para detectar perguntas sobre API
    api_query_patterns = [
        # Padrões diretos
        "quais especialidades",
        "que especialidades",
        "quais as especialidades",
        "quais são as especialidades",
        "especialidades disponíveis",
        "especialidades vocês tem",
        "especialidades tem",
        # Profissionais
        "quais profissionais",
        "que profissionais",
        "quais são os profissionais",
        "profissionais disponíveis",
        "profissionais vocês tem",
        "profissionais tem",
        # Médicos
        "quais médicos",
        "que médicos",
        "médicos disponíveis",
        "médicos vocês tem",
        "médicos tem",
        # Variações com "tem"
        "tem cardiologista",
        "tem pediatra",
        "tem ortopedista",
        "tem especialista",
        "tem doutor",
        "tem doutora",
        # Comandos de listagem
        "lista de especialidades",
        "lista de profissionais",
        "lista de médicos",
        "mostrar especialidades",
        "mostrar profissionais",
        "ver especialidades",
        "ver profissionais",
        # Variações simples
        "especialidades?",
        "profissionais?",
        "médicos?",
    ]

    # Detectar se é uma pergunta sobre API
    is_api_query = any(pattern in last_message for pattern in api_query_patterns)

    # Detecção adicional: frases que começam com palavras interrogativas
    question_words = ["quais", "que", "qual", "tem", "existe", "há"]
    medical_terms = ["especialidade", "profissional", "médico", "doutor", "doutora"]

    starts_with_question = any(last_message.startswith(word) for word in question_words)
    contains_medical_term = any(term in last_message for term in medical_terms)

    if is_api_query or (starts_with_question and contains_medical_term):
        logger.info(
            f"🎯 DETECTADO: Pergunta sobre especialidades/profissionais: '{last_message}'"
        )
        logger.info("Redirecionando para agent_tool_caller para buscar informações")

        return {
            **state,
            "next_step": "agent_tool_caller",
            "conversation_context": "api_interaction",
        }

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

            # 🔧 CORREÇÃO: Usar histórico maior para preservar contexto
            llm_service = LLMFactory.create_llm_service("openai")
            all_messages = state.get("messages", [])
            conversation_history = _format_conversation_history(
                all_messages, max_messages=12  # 
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
                    "conversation_context": "",
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

        # 🔧 CORREÇÃO PRINCIPAL: Usar histórico maior para preservar especialidade
        conversation_history = _format_conversation_history(all_messages, max_messages=10)  # 🔧 AUMENTADO DE 3 PARA 10

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
    Mescla detalhes de agendamento, priorizando informações mais recentes quando não forem None.
    🔧 CORREÇÃO: Melhor preservação de dados existentes
    """
    if not existing:
        logger.info("Nenhum detalhe existente, retornando dados novos")
        return new

    if not new:
        logger.info("Nenhum detalhe novo, retornando dados existentes")
        return existing

    # 🔧 LÓGICA MELHORADA: Priorizar valores não-None, mas preservar existentes quando novo é None
    merged = SchedulingDetails(
        professional_name=(
            new.professional_name 
            if new.professional_name is not None and new.professional_name.strip()
            else existing.professional_name
        ),
        specialty=(
            new.specialty 
            if new.specialty is not None and new.specialty.strip()
            else existing.specialty
        ),
        date_preference=(
            new.date_preference 
            if new.date_preference is not None and new.date_preference.strip()
            else existing.date_preference
        ),
        time_preference=(
            new.time_preference 
            if new.time_preference is not None and new.time_preference.strip()
            else existing.time_preference
        ),
        specific_time=(
            new.specific_time 
            if new.specific_time is not None and new.specific_time.strip()
            else existing.specific_time
        ),
        service_type=(
            new.service_type 
            if new.service_type is not None and new.service_type.strip()
            else existing.service_type
        ),
        patient_name=(
            new.patient_name 
            if new.patient_name is not None and new.patient_name.strip()
            else existing.patient_name
        ),
    )

    # 🔧 LOG DETALHADO PARA DEBUG
    logger.info(f"🔄 MERGE - Existente: {existing}")
    logger.info(f"🔄 MERGE - Novo: {new}")
    logger.info(f"🔄 MERGE - Resultado: {merged}")

    return merged
