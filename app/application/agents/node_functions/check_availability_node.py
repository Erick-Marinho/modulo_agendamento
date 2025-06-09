# app/application/agents/node_functions/check_availability_node.py

import logging
from typing import List, Tuple, Optional
from langchain_core.messages import AIMessage
from datetime import datetime

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient
from app.infrastructure.repositories.apphealth_api_medical_repository import (
    AppHealthAPIMedicalRepository,
)
from app.infrastructure.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

# --- Funções Auxiliares (Mantenha as que já existem) ---


async def _get_professional_id_by_name(
    professional_name: str, repository: AppHealthAPIMedicalRepository
) -> int | None:
    # ... (código existente sem alterações)
    all_professionals = await repository.get_api_professionals()

    normalized_input_name = (
        professional_name.lower().replace("dr.", "").replace("dra.", "").strip()
    )

    for prof in all_professionals:
        normalized_prof_name = (
            prof.nome.lower().replace("dr.", "").replace("dra.", "").strip()
        )
        if normalized_input_name in normalized_prof_name:
            logger.info(
                f"ID {prof.id} encontrado para o profissional '{professional_name}' (Match: '{prof.nome}')"
            )
            return prof.id

    logger.warning(f"Nenhum ID encontrado para o profissional '{professional_name}'")
    return None


def _filter_times_by_preference(
    available_times: List[dict], time_preference: str
) -> List[str]:
    # ... (código existente sem alterações)
    filtered = []
    for slot in available_times:
        start_hour = int(slot["horaInicio"].split(":")[0])
        if time_preference == "manha" and 5 <= start_hour < 12:
            filtered.append(slot["horaInicio"])
        elif time_preference == "tarde" and 12 <= start_hour < 18:
            filtered.append(slot["horaInicio"])
    return filtered


# --- NOVA FUNÇÃO AUXILIAR ---
async def _find_first_available_slot(
    api_client: AppHealthAPIClient,
    professional_id: int,
    time_preference: str,
    start_date: datetime,
    preferred_date_str: Optional[str] = None,
) -> Tuple[Optional[str], List[str]]:
    """
    Busca a primeira data com horários disponíveis que correspondam ao turno,
    a partir de uma data inicial.
    """
    logger.info(f"Iniciando busca de slots. Data preferida: {preferred_date_str}")
    
    # Se uma data específica foi preferida, verifique-a primeiro.
    if preferred_date_str and preferred_date_str != "invalid_date":
        logger.info(f"Verificando disponibilidade para data preferida: {preferred_date_str}")
        times_raw = await api_client.get_available_times_from_api(
            professional_id, preferred_date_str
        )
        logger.info(f"Horários brutos encontrados para {preferred_date_str}: {times_raw}")
        filtered_times = _filter_times_by_preference(times_raw, time_preference)
        logger.info(f"Horários filtrados para {preferred_date_str}: {filtered_times}")
        
        if filtered_times:
            logger.info(
                f"✅ Encontrados horários na data preferida ({preferred_date_str}): {filtered_times}"
            )
            return preferred_date_str, filtered_times
        else:
            logger.info(f"❌ Nenhum horário encontrado na data preferida ({preferred_date_str})")

    # Se a data preferida não funcionou ou não foi fornecida, procure nos próximos dias.
    logger.info(f"Buscando datas disponíveis para mês {start_date.month}/{start_date.year}")
    dates_to_check = await api_client.get_available_dates_from_api(
        professional_id, start_date.month, start_date.year
    )
    logger.info(f"Datas encontradas para verificar: {[d['data'] for d in dates_to_check]}")

    for date_info in sorted(dates_to_check, key=lambda d: d["data"]):
        date_str = date_info["data"]
        if date_str < start_date.strftime("%Y-%m-%d"):
            logger.info(f"Pulando data passada: {date_str}")
            continue  # Pula datas passadas

        logger.info(f"Verificando horários para: {date_str}")
        times_raw = await api_client.get_available_times_from_api(
            professional_id, date_str
        )
        filtered_times = _filter_times_by_preference(times_raw, time_preference)

        if filtered_times:
            logger.info(
                f"✅ Encontrado o próximo dia ({date_str}) com horários para o turno '{time_preference}': {filtered_times}"
            )
            return date_str, filtered_times
        else:
            logger.info(f"❌ Nenhum horário no turno '{time_preference}' para {date_str}")

    logger.warning("Nenhuma data com horários disponíveis encontrada")
    return None, []


# --- O Nó Principal (VERSÃO ATUALIZADA) ---


async def check_availability_node(state: MessageAgentState) -> MessageAgentState:
    logger.info("--- Executando nó check_availability (Versão Robusta 2.0) ---")
    current_messages = state.get("messages", [])
    details = state.get("extracted_scheduling_details")

    try:
        if not details:
            raise ValueError("Detalhes do agendamento não encontrados no estado.")

        api_client = AppHealthAPIClient()
        repository = AppHealthAPIMedicalRepository(api_client)
        llm_service = LLMFactory.create_llm_service("openai")

        professional_id = await _get_professional_id_by_name(
            details.professional_name, repository
        )
        if not professional_id:
            raise ValueError(
                f"Cadastro do profissional '{details.professional_name}' não encontrado."
            )

        today = datetime.now()
        logger.info(f"Data atual: {today.strftime('%Y-%m-%d')}")
        logger.info(f"Preferência do usuário: '{details.date_preference}'")
        
        translated_date = llm_service.translate_natural_date(
            user_preference=details.date_preference,
            current_date=today.strftime("%Y-%m-%d"),
        )
        
        logger.info(f"Data traduzida pelo LLM: '{translated_date}'")

        # Busca o primeiro dia com horários que batem com a preferência
        found_date, suggested_times = await _find_first_available_slot(
            api_client,
            professional_id,
            details.time_preference,
            today,
            translated_date if translated_date != "invalid_date" else None,
        )

        logger.info(f"Data encontrada: '{found_date}', Horários: {suggested_times}")

        if found_date and suggested_times:
            times_str = ", ".join([t[:5] for t in suggested_times])
            date_formatted = datetime.strptime(found_date, "%Y-%m-%d").strftime(
                "%d/%m/%Y"
            )

            # NOVA LÓGICA: Comparação mais inteligente
            is_same_date = (translated_date == found_date) and (translated_date != "invalid_date")
            
            if is_same_date:
                response_text = f"Perfeito! Para o dia {date_formatted}, encontrei os seguintes horários com o(a) {details.professional_name} no período da {details.time_preference}: {times_str}. Qual você prefere?"
            else:
                # Verifica se o usuário pediu uma data específica ou genérica
                user_asked_specific_day = any(word in details.date_preference.lower() for word in ["dia", "hoje", "amanhã"])
                
                if user_asked_specific_day and translated_date != "invalid_date":
                    original_date_formatted = datetime.strptime(translated_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                    response_text = f"Não encontrei horários disponíveis para o dia {original_date_formatted} que você pediu. No entanto, na data mais próxima disponível ({date_formatted}), tenho estes horários na {details.time_preference}: {times_str}. Algum desses te interessa?"
                else:
                    response_text = f"Encontrei os seguintes horários disponíveis com o(a) Dr(a). {details.professional_name} para o dia {date_formatted} no período da {details.time_preference}: {times_str}. Qual você prefere?"

            return {
                **state,
                "messages": current_messages + [AIMessage(content=response_text)],
                "conversation_context": "awaiting_slot_selection",
                "next_step": "completed",
            }

        else:  # Se não encontrou NENHUM horário em NENHUM dia
            response_text = f"Puxa, parece que o(a) {details.professional_name} não possui horários disponíveis no período da {details.time_preference} para este mês. Gostaria de tentar no próximo mês ou para outro turno?"
            return {
                **state,
                "messages": current_messages + [AIMessage(content=response_text)],
                "conversation_context": "awaiting_new_date_selection",
                "next_step": "completed",
            }

    except Exception as e:
        logger.error(
            f"Erro crítico inesperado no nó check_availability: {e}", exc_info=True
        )
        error_message = AIMessage(
            content="Desculpe, tive uma dificuldade em consultar a agenda. Poderia tentar novamente em alguns instantes?"
        )
        return {
            **state,
            "messages": current_messages + [error_message],
            "next_step": "completed",
        }
