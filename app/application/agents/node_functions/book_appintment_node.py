# app/application/agents/node_functions/book_appointment_node.py
import logging
import re
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient
from app.infrastructure.repositories.apphealth_api_medical_repository import AppHealthAPIMedicalRepository

logger = logging.getLogger(__name__)

# --- Funções Auxiliares (sem alterações) ---

def _extract_time_from_message(message: str) -> str | None:
    match = re.search(r'\b(\d{1,2}:\d{2})\b', message)
    if match:
        return match.group(1)
    return None

async def _get_specialty_id_by_name(specialty_name: str, repository: AppHealthAPIMedicalRepository) -> int | None:
    if not specialty_name: return None
    all_specialties = await repository.get_all_api_specialties()
    for spec in all_specialties:
        if spec.especialidade.strip().lower() == specialty_name.strip().lower():
            return spec.id
    return None

# --- O Nó Final (Versão Robusta) ---

async def book_appointment_node(state: MessageAgentState) -> MessageAgentState:
    logger.info("--- Executando nó book_appointment (Implementação Final e Robusta) ---")
    current_messages = state.get("messages", [])
    details = state.get("extracted_scheduling_details")

    try:
        # 1. Extrair horário da última mensagem do usuário
        last_user_message = next((msg.content for msg in reversed(current_messages) if isinstance(msg, HumanMessage)), None)
        chosen_time = _extract_time_from_message(last_user_message)
        if not chosen_time:
            raise ValueError(f"Não foi possível extrair um horário da mensagem: '{last_user_message}'")

        # 2. Instanciar dependências
        api_client = AppHealthAPIClient()
        repository = AppHealthAPIMedicalRepository(api_client)

        # 3. Obter IDs necessários de forma segura
        professional_id = (await repository.get_professionals_by_specialty_name(details.specialty) or await repository.get_api_professionals())[0].id
        specialty_id = await _get_specialty_id_by_name(details.specialty, repository)

        # 4. Montar a data do agendamento
        day_number = int(re.search(r'\d+', details.date_preference).group())
        today = datetime.now()
        # Lógica para evitar agendar em um mês passado se o dia for menor que o atual
        target_month = today.month if day_number >= today.day else today.month + 1
        data_agendamento = today.replace(month=target_month, day=day_number).strftime("%Y-%m-%d")

        # 5. Construir o payload base
        payload = {
            "data": data_agendamento,
            "horaInicio": f"{chosen_time}:00",
            "horaFim": f"{int(chosen_time.split(':')[0]) + 1:02d}:{chosen_time.split(':')[1]}:00",
            "nome": "Paciente Agendado via Chatbot",
            "telefonePrincipal": state.get("phone_number", ""),
            "situacao": "AGENDADO",
            "profissionalSaude": {"id": professional_id},
            "paciente": {"nome": "Paciente Agendado via Chatbot"},
            "unidade": {"id": 1} # Usando um ID de unidade padrão
        }

        # 6. Adicionar a especialidade APENAS se ela existir
        if specialty_id:
            payload["especialidade"] = {"id": specialty_id}

        logger.info(f"Payload final para agendamento: {payload}")

        # 7. Chamar a API de agendamento
        await api_client.book_appointment_on_api(payload)
        
        # 8. Gerar mensagem de sucesso
        data_formatada = datetime.strptime(data_agendamento, "%Y-%m-%d").strftime("%d/%m/%Y")
        response_text = f"Pronto! Agendamento confirmado com sucesso para o dia {data_formatada} às {chosen_time} com Dr(a). {details.professional_name}. Obrigado por utilizar nossos serviços!"
        
    except Exception as e:
        logger.error(f"Erro crítico no nó de agendamento: {e}", exc_info=True)
        response_text = "Tive um problema ao tentar confirmar seu agendamento no sistema. Por favor, tente novamente em alguns instantes ou entre em contato com nossa central."

    final_message = AIMessage(content=response_text)
    return {
        **state,
        "messages": current_messages + [final_message],
        "next_step": "completed"
    }