# app/application/agents/node_functions/check_availability_node.py
import logging
from typing import List
from langchain_core.messages import AIMessage
from datetime import datetime

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient
from app.infrastructure.repositories.apphealth_api_medical_repository import AppHealthAPIMedicalRepository

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

async def check_availability_node(state: MessageAgentState) -> MessageAgentState:
    """
    Nó para verificar a disponibilidade de um profissional, sugerir horários e
    aguardar a seleção final do usuário.
    """
    logger.info("--- Executando nó check_availability ---")
    current_messages = state.get("messages", [])
    details = state.get("extracted_scheduling_details")

    if not details:
        # Fallback caso algo dê muito errado
        error_message = AIMessage(content="Ocorreu um erro e não consegui verificar a agenda. Por favor, tente iniciar o agendamento novamente.")
        return {**state, "messages": current_messages + [error_message], "next_step": "completed"}

    # 1. Instanciar nossas dependências
    api_client = AppHealthAPIClient()
    repository = AppHealthAPIMedicalRepository(api_client)

    # 2. Obter ID do profissional
    professional_id = await _get_professional_id_by_name(details.professional_name, repository)
    if not professional_id:
        msg = AIMessage(content=f"Não encontrei o cadastro do profissional '{details.professional_name}'. Por favor, verifique o nome e tente novamente.")
        return {**state, "messages": current_messages + [msg], "next_step": "completed"}

    # Lógica a ser implementada:
    # 3. Obter o mês e ano atual para a busca
    today = datetime.now()
    month, year = today.month, today.year

    # 4. Chamar a API de datas
    available_dates_raw = await api_client.get_available_dates_from_api(professional_id, month, year)
    if not available_dates_raw:
        msg = AIMessage(content=f"O profissional '{details.professional_name}' não possui agenda disponível para este mês. Gostaria de tentar no próximo mês?")
        return {**state, "messages": current_messages + [msg], "next_step": "awaiting_new_date_selection"} # Novo estado

    # 5. "Traduzir" a preferência do usuário (ex: "terça") para datas reais (ex: ["2025-06-10", "2025-06-17"])
    #    Esta é uma tarefa complexa. Uma abordagem seria usar o LLM para isso.
    #    Por agora, vamos SIMPLIFICAR: pegaremos as 3 primeiras datas disponíveis.
    
    suggested_dates = [d["data"] for d in available_dates_raw[:3]] # Simplificação por agora
    
    # 6. Para a primeira data sugerida, buscar os horários e filtrar pelo turno
    first_date_to_check = suggested_dates[0]
    available_times_raw = await api_client.get_available_times_from_api(professional_id, first_date_to_check)
    
    suggested_times = _filter_times_by_preference(available_times_raw, details.time_preference)

    # 7. Construir a resposta para o usuário
    if suggested_times:
        times_str = ", ".join([t[:5] for t in suggested_times]) # Formato HH:MM
        date_formatted = datetime.strptime(first_date_to_check, "%Y-%m-%d").strftime("%d/%m/%Y")
        response_text = f"Ótimo! Para a data mais próxima ({date_formatted}), o(a) Dr(a). {details.professional_name} tem os seguintes horários disponíveis no período da {details.time_preference}: {times_str}. Qual você prefere?"
        next_step = "awaiting_slot_selection"
    else:
        # Se não há horários no turno, sugerir outras datas
        dates_str = ", ".join([datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in suggested_dates])
        response_text = f"Para a sua preferência de data, não encontrei horários no período da {details.time_preference}. As próximas datas disponíveis são: {dates_str}. Alguma delas te interessa?"
        next_step = "awaiting_new_date_selection"

    # 8. Atualizar o estado
    new_message = AIMessage(content=response_text)
    
    return {
        **state,
        "messages": current_messages + [new_message],
        "conversation_context": next_step, # Usaremos isso no orquestrador
        "next_step": "completed" # O fluxo do agente para aqui e aguarda a resposta do usuário
    }