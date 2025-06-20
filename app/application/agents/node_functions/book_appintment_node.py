import logging
import re
from datetime import datetime
from typing import List

import httpx
from langchain_core.messages import AIMessage, HumanMessage

from app.application.agents.state.message_agent_state import MessageAgentState
from app.domain.entities.medical_professional import ApiMedicalProfessional
from app.domain.sheduling_details import SchedulingDetails
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient
from app.infrastructure.repositories.apphealth_api_medical_repository import (
    AppHealthAPIMedicalRepository,
)

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
        if hasattr(msg, "content") and isinstance(msg.content, str):
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
    """Busca o ID de um profissional pelo nome com correspondência bidirecional melhorada."""
    all_professionals = await repository.get_api_professionals()
    normalized_input_name = (
        professional_name.lower().replace("dr.", "").replace("dra.", "").strip()
    )
    for prof in all_professionals:
        normalized_prof_name = (
            prof.nome.lower().replace("dr.", "").replace("dra.", "").strip()
        )

        # 🆕 LÓGICA BIDIRECIONAL MELHORADA
        # Verifica correspondência nos dois sentidos
        is_match = (
            normalized_input_name in normalized_prof_name
            or normalized_prof_name in normalized_input_name
        )

        # 🆕 CORRESPONDÊNCIA POR PALAVRAS-CHAVE
        # Para casos como "Clara" → "Clara Joaquina" ou "João Silva" → "Dr. João"
        input_words = set(normalized_input_name.split())
        prof_words = set(normalized_prof_name.split())

        # Se pelo menos 1 palavra do input está no nome do profissional
        word_match = bool(input_words.intersection(prof_words))

        if is_match or word_match:
            logger.info(
                f"✅ ID {prof.id} encontrado para '{professional_name}' "
                f"(Match: '{prof.nome}') - "
                f"Método: {'substring' if is_match else 'palavras'}"
            )
            return prof.id
    logger.warning(f"❌ Nenhum ID encontrado para o profissional '{professional_name}'")
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


def _filter_times_by_preference(
    available_times: List[dict], time_preference: str
) -> List[str]:
    """Filtra horários por preferência de turno."""
    MORNING_RANGE = (5, 12)
    AFTERNOON_RANGE = (12, 18)

    filtered = []
    for slot in available_times:
        start_hour = int(slot["horaInicio"].split(":")[0])
        
        if (
            time_preference == "manha"
            and MORNING_RANGE[0] <= start_hour < MORNING_RANGE[1]
        ):
            filtered.append(slot["horaInicio"])
        elif (
            time_preference == "tarde"
            and AFTERNOON_RANGE[0] <= start_hour < AFTERNOON_RANGE[1]
        ):
            filtered.append(slot["horaInicio"])
    return filtered


async def _validate_time_availability(
    api_client: AppHealthAPIClient,
    professional_id: int,
    date: str,
    chosen_time: str,
    time_preference: str
) -> tuple[bool, list[str]]:
    """
    Valida se o horário escolhido está disponível.
    Retorna: (is_valid, available_times_list)
    """
    try:
        # Buscar horários disponíveis da API
        available_slots = await api_client.get_available_times_from_api(
            professional_id, date
        )
        
        # Filtrar por turno
        filtered_times = _filter_times_by_preference(available_slots, time_preference)
        
        # Verificar se o horário escolhido está disponível
        chosen_time_formatted = f"{chosen_time}:00"
        is_available = chosen_time_formatted in [slot["horaInicio"] for slot in available_slots]
        
        return is_available, filtered_times
    except Exception as e:
        logger.error(f"Erro ao validar disponibilidade: {e}")
        return False, []


# --- O Nó Final (Versão Corrigida) ---


async def book_appointment_node(state: MessageAgentState) -> MessageAgentState:
    logger.info(
        "--- Executando nó book_appointment (Versão Corrigida com specific_time) ---"
    )
    current_messages = state.get("messages", [])
    details = state.get("extracted_scheduling_details")

    try:
        # 1. Validações iniciais
        if not details:
            raise ValueError("Detalhes do agendamento não encontrados no estado.")

        logger.info(f"Detalhes do agendamento: {details}")

        # 🕵️ DEBUG DETALHADO
        logger.info("=== DEBUG HORÁRIO ===")
        logger.info(f"Tipo de details: {type(details)}")
        logger.info(f"É dict? {isinstance(details, dict)}")

        if isinstance(details, dict):
            logger.info(
                f"specific_time no dict: {details.get('specific_time', 'NÃO ENCONTRADO')}"
            )
            chosen_time = details.get("specific_time")
        else:
            logger.info(f"hasattr specific_time? {hasattr(details, 'specific_time')}")
            logger.info(
                f"specific_time valor: {getattr(details, 'specific_time', 'NÃO ENCONTRADO')}"
            )
            chosen_time = (
                details.specific_time if hasattr(details, "specific_time") else None
            )

        logger.info(f"chosen_time ANTES do fallback: {chosen_time}")

        # Se não encontrou, usar fallback
        if not chosen_time:
            last_user_message = next(
                (
                    msg.content
                    for msg in reversed(current_messages)
                    if isinstance(msg, HumanMessage)
                ),
                None,
            )
            logger.info(f"Última mensagem do usuário: '{last_user_message}'")
            chosen_time = _extract_time_from_message(last_user_message)
            logger.info(f"Horário extraído da mensagem: {chosen_time}")

        logger.info(f"🎯 HORÁRIO FINAL: {chosen_time}")
        logger.info("=====================")

        # 3. Extrair data das mensagens da conversa
        appointment_date = _extract_date_from_conversation(current_messages)
        if not appointment_date:
            raise ValueError(
                "Não foi possível extrair a data do agendamento das mensagens."
            )

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

        # ✅ CORREÇÃO: Só buscar specialty_id se specialty não for None
        specialty_id = None
        if details.specialty:
            specialty_id = await _get_specialty_id_by_name(details.specialty, repository)
            logger.info(f"Specialty ID encontrado: {specialty_id} para '{details.specialty}'")
        else:
            logger.warning("Specialty é None - agendando sem especialidade específica")

        logger.info(f"Professional ID: {professional_id}, Specialty ID: {specialty_id}")

        # 🚨 VALIDAÇÃO CRÍTICA - Verificar se horário está disponível ANTES de agendar
        logger.info(f"🔍 Validando horário {chosen_time} para data {appointment_date}")
        is_valid, available_times = await _validate_time_availability(
            api_client, professional_id, appointment_date, 
            chosen_time, details.time_preference
        )

        if not is_valid:
            # ❌ Horário inválido - solicitar nova escolha
            times_list = [t[:5] for t in available_times]
            formatted_times = "\n".join(times_list)
            date_formatted = datetime.strptime(appointment_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            
            error_message = (
                f"Desculpe, o horário {chosen_time} não está disponível. "
                f"Os horários disponíveis para {details.professional_name} "
                f"no dia {date_formatted} no período da {details.time_preference} são:\n\n"
                f"{formatted_times}\n\n"
                f"Por favor, escolha um dos horários disponíveis."
            )
            
            logger.info(f"❌ Horário {chosen_time} rejeitado - solicitando nova escolha")
            
            return {
                **state,
                "messages": current_messages + [AIMessage(content=error_message)],
                "conversation_context": "awaiting_slot_selection",
                "next_step": "completed",
            }

        # ✅ Horário válido - prosseguir com agendamento
        logger.info(f"✅ Horário {chosen_time} validado com sucesso!")

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
            "unidade": {"id": 21641},
        }

        # ✅ CORREÇÃO CRÍTICA: Só adicionar especialidade se for encontrada e não for None
        if specialty_id:
            payload["especialidade"] = {"id": specialty_id}
            logger.info(f"Adicionando especialidade {specialty_id} ao payload")
        else:
            logger.warning("Agendando sem especialidade específica no payload")

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
        date_formatted = datetime.strptime(appointment_date, "%Y-%m-%d").strftime(
            "%d/%m/%Y"
        )
        response_text = f"Agendamento confirmado com sucesso para o dia {date_formatted} às {chosen_time} com {details.professional_name}. Obrigado por utilizar nossos serviços!"

        # ✅ 11. Atualizar estado com horário escolhido (incluindo specific_time)
        # Converter SchedulingDetails para dict se necessário
        if hasattr(details, "model_dump"):
            updated_details = SchedulingDetails(
                **{**details.model_dump(), "specific_time": chosen_time}
            )
        else:
            # Fallback para quando details já é um dict
            details_dict = details if isinstance(details, dict) else details.__dict__
            updated_details = SchedulingDetails(
                **{**details_dict, "specific_time": chosen_time}
            )

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
