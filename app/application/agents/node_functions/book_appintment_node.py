import logging
import re
from datetime import datetime
from typing import List
from langchain_core.messages import AIMessage, HumanMessage

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient
from app.infrastructure.repositories.apphealth_api_medical_repository import AppHealthAPIMedicalRepository
from app.domain.entities.medical_professional import ApiMedicalProfessional

logger = logging.getLogger(__name__)


# --- Funções Auxiliares (Reutilizadas do nó anterior) ---

def _extract_time_from_message(message: str) -> str | None:
    """Extrai um horário no formato HH:MM de uma string usando regex."""
    if not message: return None
    match = re.search(r'\b(\d{1,2}:\d{2})\b', message)
    if match:
        return match.group(1)
    return None

async def _get_professional_id_by_name(professional_name: str, repository: AppHealthAPIMedicalRepository) -> int | None:
    """Busca o ID de um profissional pelo nome de forma flexível."""
    all_professionals = await repository.get_api_professionals()
    normalized_input_name = professional_name.lower().replace("dr.", "").replace("dra.", "").strip()
    for prof in all_professionals:
        normalized_prof_name = prof.nome.lower().replace("dr.", "").replace("dra.", "").strip()
        if normalized_input_name in normalized_prof_name:
            logger.info(f"ID {prof.id} encontrado para o profissional '{professional_name}' (Match: '{prof.nome}')")
            return prof.id
    logger.warning(f"Nenhum ID encontrado para o profissional '{professional_name}'")
    return None

async def _get_specialty_id_by_name(specialty_name: str, repository: AppHealthAPIMedicalRepository) -> int | None:
    """Busca o ID de uma especialidade pelo nome."""
    if not specialty_name: return None
    all_specialties = await repository.get_all_api_specialties()
    for spec in all_specialties:
        if spec.especialidade.strip().lower() == specialty_name.strip().lower():
            return spec.id
    return None

# --- O Nó Final (Versão Corrigida) ---

async def book_appointment_node(state: MessageAgentState) -> MessageAgentState:
    logger.info("--- Executando nó book_appointment (Implementação Final e Corrigida) ---")
    current_messages = state.get("messages", [])
    details = state.get("extracted_scheduling_details")

    try:
        # 1. Extrair horário da última mensagem
        last_user_message = next((msg.content for msg in reversed(current_messages) if isinstance(msg, HumanMessage)), None)
        chosen_time = _extract_time_from_message(last_user_message)
        if not chosen_time:
            raise ValueError(f"Não foi possível extrair um horário da mensagem: '{last_user_message}'")

        # 2. Instanciar dependências
        api_client = AppHealthAPIClient()
        repository = AppHealthAPIMedicalRepository(api_client)

        # 3. Obter IDs de forma segura USANDO O NOME
        professional_id = await _get_professional_id_by_name(details.professional_name, repository)
        if not professional_id:
            raise ValueError(f"Não foi possível encontrar o ID para o profissional '{details.professional_name}' no passo final.")
            
        specialty_id = await _get_specialty_id_by_name(details.specialty, repository)

        # 4. Montar a data do agendamento
        day_number_match = re.search(r'\d+', details.date_preference)
        if not day_number_match:
             # Fallback se a preferência de data não tiver um número (ex: "próxima segunda")
             # Neste ponto, o agente já deveria ter uma data concreta, mas é uma segurança
             translated_date_from_context = state.get("messages", [])[-2].content.split('(')[1].split(')')[0] # Pega a data da mensagem anterior do AI
             data_agendamento = datetime.strptime(translated_date_from_context, "%d/%m/%Y").strftime("%Y-%m-%d")
        else:
             day_number = int(day_number_match.group())
             today = datetime.now()
             target_month = today.month if day_number >= today.day else today.month + 1
             data_agendamento = today.replace(month=target_month, day=day_number).strftime("%Y-%m-%d")
        
        # 5. Construir o payload
        payload = {
            "data": data_agendamento,
            "horaInicio": f"{chosen_time}:00",
            "horaFim": f"{int(chosen_time.split(':')[0]) + 1:02d}:{chosen_time.split(':')[1]}:00",
            "nome": "Paciente Agendado via Chatbot",
            "telefonePrincipal": state.get("phone_number", ""),
            "situacao": "AGENDADO",
            "profissionalSaude": {"id": professional_id},
            "paciente": {"nome": "Paciente Agendado via Chatbot"},
            "unidade": {"id": 1}
        }
        
        if specialty_id:
            payload["especialidade"] = {"id": specialty_id}

        logger.info(f"Payload final para agendamento: {payload}")

        # 6. Chamar a API de agendamento
        await api_client.book_appointment_on_api(payload)
        
        data_formatada = datetime.strptime(data_agendamento, "%Y-%m-%d").strftime("%d/%m/%Y")
        response_text = f"Pronto! Agendamento confirmado com sucesso para o dia {data_formatada} às {chosen_time} com {details.professional_name}. Obrigado por utilizar nossos serviços!"
        
    except Exception as e:
        logger.error(f"Erro crítico no nó de agendamento: {e}", exc_info=True)
        response_text = "Tive um problema ao tentar confirmar seu agendamento no sistema. Por favor, tente novamente em alguns instantes ou entre em contato com nossa central."

    final_message = AIMessage(content=response_text)
    return {**state, "messages": current_messages + [final_message], "conversation_context": "completed", "next_step": "completed"}
