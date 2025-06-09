import logging
import re
from datetime import datetime
from typing import List
from langchain_core.messages import AIMessage, HumanMessage
import httpx

from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient
from app.infrastructure.repositories.apphealth_api_medical_repository import (
    AppHealthAPIMedicalRepository,
)
from app.domain.entities.medical_professional import ApiMedicalProfessional

logger = logging.getLogger(__name__)


# --- Funções Auxiliares (Reutilizadas do nó anterior) ---


def _extract_time_from_message(message: str) -> str | None:
    """Extrai um horário no formato HH:MM de uma string usando regex."""
    if not message:
        return None
    match = re.search(r"\b(\d{1,2}:\d{2})\b", message)
    if match:
        return match.group(1)
    return None


def _extract_date_from_conversation(messages: List) -> str | None:
    """Extrai a data do agendamento das mensagens anteriores."""
    for msg in reversed(messages):
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            # Procura por data no formato DD/MM/YYYY
            date_match = re.search(r"(\d{2}/\d{2}/\d{4})", msg.content)
            if date_match:
                date_str = date_match.group(1)
                try:
                    # Converte para formato YYYY-MM-DD
                    parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return None


async def _get_professional_id_by_name(
    professional_name: str, repository: AppHealthAPIMedicalRepository
) -> int | None:
    """Busca o ID de um profissional pelo nome de forma flexível."""
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


async def _get_specialty_id_by_name(
    specialty_name: str, repository: AppHealthAPIMedicalRepository
) -> int | None:
    """Busca o ID de uma especialidade pelo nome."""
    if not specialty_name:
        return None
    all_specialties = await repository.get_all_api_specialties()
    for spec in all_specialties:
        if spec.especialidade.strip().lower() == specialty_name.strip().lower():
            return spec.id
    return None


# --- O Nó Final (Versão Corrigida) ---


async def book_appointment_node(state: MessageAgentState) -> MessageAgentState:
    logger.info("--- Executando nó book_appointment (Versão Corrigida) ---")
    current_messages = state.get("messages", [])
    details = state.get("extracted_scheduling_details")

    try:
        # 1. Validações iniciais
        if not details:
            raise ValueError("Detalhes do agendamento não encontrados no estado.")

        logger.info(f"Detalhes do agendamento: {details}")

        # 2. Extrair horário escolhido da última mensagem do usuário
        last_user_message = next(
            (
                msg.content
                for msg in reversed(current_messages)
                if isinstance(msg, HumanMessage)
            ),
            None,
        )
        
        chosen_time = _extract_time_from_message(last_user_message)
        if not chosen_time:
            raise ValueError(
                f"Não foi possível extrair um horário da mensagem: '{last_user_message}'"
            )
        
        logger.info(f"Horário escolhido extraído: {chosen_time}")

        # 3. Extrair data das mensagens da conversa
        appointment_date = _extract_date_from_conversation(current_messages)
        if not appointment_date:
            raise ValueError("Não foi possível extrair a data do agendamento das mensagens.")
        
        logger.info(f"Data do agendamento extraída: {appointment_date}")

        # 4. Instanciar dependências
        api_client = AppHealthAPIClient()
        repository = AppHealthAPIMedicalRepository(api_client)

        # 5. Obter IDs necessários
        professional_id = await _get_professional_id_by_name(
            details.professional_name, repository
        )
        if not professional_id:
            raise ValueError(
                f"Não foi possível encontrar o ID para o profissional '{details.professional_name}'"
            )

        specialty_id = await _get_specialty_id_by_name(details.specialty, repository)
        
        logger.info(f"Professional ID: {professional_id}, Specialty ID: {specialty_id}")

        # 6. Calcular hora de fim (1 hora após o início)
        start_hour, start_minute = chosen_time.split(":")
        end_hour = int(start_hour) + 1
        end_time = f"{end_hour:02d}:{start_minute}"

        # 7. Construir o payload
        payload = {
            "data": appointment_date,
            "horaInicio": f"{chosen_time}:00",
            "horaFim": f"{end_time}:00",
            "nome": "Paciente Agendado via Chatbot",
            "telefonePrincipal": state.get("phone_number", ""),
            "situacao": "AGENDADO",
            "profissionalSaude": {"id": professional_id},
            "paciente": {"nome": "Paciente Agendado via Chatbot"},
            "unidade": {"id": 1},
        }

        if specialty_id:
            payload["especialidade"] = {"id": specialty_id}

        logger.info(f"Payload final para agendamento: {payload}")

        # 8. Chamar a API de agendamento
        try:
            result = await api_client.book_appointment_on_api(payload)
            logger.info(f"Agendamento realizado com sucesso: {result}")
        except Exception as api_error:
            logger.error(f"Erro na API de agendamento: {api_error}")
            raise api_error

        # 9. Remover tag após agendamento bem-sucedido
        phone_number = state.get("phone_number", "")
        if phone_number:
            try:
                remove_tag_url = f"https://n8n-server.apphealth.com.br/webhook/remove-tag?phone={phone_number}"
                async with httpx.AsyncClient() as client:
                    remove_response = await client.get(remove_tag_url, timeout=5.0)
                    remove_response.raise_for_status()
                    logger.info(f"Tag removida com sucesso para {phone_number}")
            except Exception as tag_error:
                logger.warning(f"Erro ao remover tag para {phone_number}: {tag_error}")
                # Não falha o agendamento se não conseguir remover a tag

        # 10. Gerar mensagem de sucesso
        date_formatted = datetime.strptime(appointment_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        response_text = f"Perfeito! Agendamento confirmado com sucesso para o dia {date_formatted} às {chosen_time} com {details.professional_name}. Obrigado por utilizar nossos serviços!"

        # 11. Atualizar estado com horário escolhido
        details_dict = details.__dict__ if hasattr(details, '__dict__') else details
        updated_details = {
            **details_dict,
            "time_preference": details.time_preference,
            "specific_time": chosen_time
        }

        final_message = AIMessage(content=response_text)
        return {
            **state,
            "messages": current_messages + [final_message],
            "extracted_scheduling_details": updated_details,
            "missing_fields": [],  # Limpar campos faltantes
            "conversation_context": "completed",
            "next_step": "completed",
        }

    except Exception as e:
        logger.error(f"Erro crítico no nó de agendamento: {e}", exc_info=True)
        
        # Mensagem de erro mais específica baseada no tipo de erro
        if "API" in str(e) or "HTTP" in str(e):
            response_text = "Tive um problema de conexão com o sistema de agendamentos. Por favor, tente novamente em alguns instantes ou entre em contato com nossa central."
        elif "ID" in str(e) or "profissional" in str(e).lower():
            response_text = "Houve um problema ao localizar o profissional no sistema. Por favor, entre em contato com nossa central para finalizar o agendamento."
        elif "horário" in str(e).lower() or "time" in str(e).lower():
            response_text = "Não consegui processar o horário escolhido. Por favor, informe novamente o horário desejado."
        else:
            response_text = "Tive um problema ao tentar confirmar seu agendamento no sistema. Por favor, tente novamente em alguns instantes ou entre em contato com nossa central."

        final_message = AIMessage(content=response_text)
        return {
            **state,
            "messages": current_messages + [final_message],
            "conversation_context": "error",
            "next_step": "completed",
        }
