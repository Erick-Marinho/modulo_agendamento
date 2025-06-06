import logging
from typing import List
from langchain_core.messages import AIMessage
from datetime import datetime

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient
from app.infrastructure.repositories.apphealth_api_medical_repository import AppHealthAPIMedicalRepository
from app.infrastructure.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

# --- Funções Auxiliares (vamos precisar delas) ---

async def _get_professional_id_by_name(professional_name: str, repository: AppHealthAPIMedicalRepository) -> int | None:
    """Busca o ID de um profissional pelo nome de forma flexível."""
    all_professionals = await repository.get_api_professionals()
    
    normalized_input_name = professional_name.lower().replace("dr.", "").replace("dra.", "").strip()
    
    for prof in all_professionals:
        normalized_prof_name = prof.nome.lower().replace("dr.", "").replace("dra.", "").strip()
        
        # --- LÓGICA DE BUSCA MELHORADA ---
        # Verifica se o nome fornecido pelo usuário está contido no nome completo da API
        if normalized_input_name in normalized_prof_name:
            logger.info(f"ID {prof.id} encontrado para o profissional '{professional_name}' (Match: '{prof.nome}')")
            return prof.id
            
    logger.warning(f"Nenhum ID encontrado para o profissional '{professional_name}'")
    return None

def _filter_times_by_preference(available_times: List[dict], time_preference: str) -> List[str]:
    """Filtra horários (formato HH:MM:SS) com base na preferência 'manha' ou 'tarde'."""
    filtered = []
    for slot in available_times:
        start_hour = int(slot["horaInicio"].split(":")[0])
        if time_preference == "manha" and 5 <= start_hour < 12:
            filtered.append(slot["horaInicio"])
        elif time_preference == "tarde" and 12 <= start_hour < 18:
            filtered.append(slot["horaInicio"])
    return filtered


# --- O Nó Principal ---

# Em app/application/agents/node_functions/check_availability_node.py

async def check_availability_node(state: MessageAgentState) -> MessageAgentState:
    logger.info("--- Executando nó check_availability (Versão Robusta) ---")
    current_messages = state.get("messages", [])
    details = state.get("extracted_scheduling_details")
    
    # Adicionamos um bloco try...except para capturar qualquer erro inesperado
    try:
        if not details:
            raise ValueError("Detalhes do agendamento não encontrados no estado.")

        # 1. Instanciar dependências
        api_client = AppHealthAPIClient()
        repository = AppHealthAPIMedicalRepository(api_client)

        # 2. Obter ID do profissional
        professional_id = await _get_professional_id_by_name(details.professional_name, repository)
        if not professional_id:
            raise ValueError(f"Cadastro do profissional '{details.professional_name}' não encontrado.")

        # 3. Obter datas disponíveis
        today = datetime.now()
        available_dates_raw = await api_client.get_available_dates_from_api(professional_id, today.month, today.year)
        if not available_dates_raw:
            response_text = f"O profissional '{details.professional_name}' não possui agenda disponível para este mês. Gostaria de tentar no próximo mês?"
            return {**state, "messages": current_messages + [AIMessage(content=response_text)], "conversation_context": "awaiting_new_date_selection", "next_step": "completed"}

        available_dates_list = [d.get("data") for d in available_dates_raw if d.get("data")]

        # 4. Traduzir e verificar a data
        llm_service = LLMFactory.create_llm_service("openai")
        translated_date = llm_service.translate_natural_date(
            user_preference=details.date_preference,
            current_date=today.strftime("%Y-%m-%d")
        )

        date_to_check = None
        match_found = False
        if translated_date != "invalid_date" and translated_date in available_dates_list:
            date_to_check = translated_date
            match_found = True
        else:
            date_to_check = available_dates_list[0]

        # 5. Buscar horários para a data decidida
        available_times_raw = await api_client.get_available_times_from_api(professional_id, date_to_check)
        
        # INICIALIZAÇÃO DEFENSIVA: Garante que a variável sempre exista.
        suggested_times = [] 
        suggested_times = _filter_times_by_preference(available_times_raw, details.time_preference)

        # 6. Construir a resposta
        if suggested_times:
            times_str = ", ".join([t[:5] for t in suggested_times])
            date_formatted = datetime.strptime(date_to_check, "%Y-%m-%d").strftime("%d/%m/%Y")
            
            if match_found:
                 response_text = f"Perfeito! Para {details.date_preference} ({date_formatted}), encontrei os seguintes horários com o(a) Dr(a). {details.professional_name} no período da {details.time_preference}: {times_str}. Qual você prefere?"
            else:
                 response_text = f"Não encontrei horários para a data exata que você pediu. Na data mais próxima disponível ({date_formatted}), tenho os seguintes horários na {details.time_preference}: {times_str}. Algum desses serve?"
            
            next_step = "awaiting_slot_selection"
        else:
            suggested_dates_formatted = ", ".join([datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in available_dates_list[:3]])
            response_text = f"Para a data verificada ({datetime.strptime(date_to_check, '%Y-%m-%d').strftime('%d/%m/%Y')}), não encontrei horários disponíveis no período da {details.time_preference}. As próximas datas com agenda são: {suggested_dates_formatted}. Alguma delas te interessa?"
            next_step = "awaiting_new_date_selection"

        # 7. Atualizar o estado
        return {
            **state,
            "messages": current_messages + [AIMessage(content=response_text)],
            "conversation_context": next_step,
            "next_step": "completed"
        }

    except Exception as e:
        logger.error(f"Erro crítico inesperado no nó check_availability: {e}", exc_info=True)
        # Mensagem de erro genérica para o usuário
        error_message = AIMessage(content="Desculpe, tive uma dificuldade em consultar a agenda. Poderia tentar novamente em alguns instantes?")
        return {**state, "messages": current_messages + [error_message], "next_step": "completed"}
