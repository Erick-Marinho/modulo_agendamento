# app/application/agents/node_functions/check_availability_node.py

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from langchain_core.messages import AIMessage

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
    """
    Busca o ID de um profissional pelo nome com correspondência bidirecional melhorada.
    """
    all_professionals = await repository.get_api_professionals()

    def normalize_name(name: str) -> str:
        return name.lower().replace("dr.", "").replace("dra.", "").strip()

    normalized_input_name = normalize_name(professional_name)

    for prof in all_professionals:
        normalized_prof_name = normalize_name(prof.nome)

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
    
    # 🆕 LIMITE MÁXIMO: Apenas 3 horários
    return filtered[:3]


# --- NOVA FUNÇÃO AUXILIAR ---
async def _find_first_available_slot(
    api_client: AppHealthAPIClient,
    professional_id: int,
    time_preference: str,
    start_date: datetime,
    preferred_date_str: Optional[str] = None,
) -> Tuple[Optional[str], List[str], bool]:
    """
    Busca a primeira data com horários disponíveis que correspondam ao turno,
    a partir de uma data inicial.
    Retorna: (data_encontrada, horarios, data_preferida_foi_encontrada)
    """
    logger.info(f"🔍 Iniciando busca de slots. Data preferida: {preferred_date_str}")

    # Buscar todas as datas disponíveis primeiro
    logger.info(
        f"Buscando datas disponíveis para mês {start_date.month}/{start_date.year}"
    )
    dates_to_check = await api_client.get_available_dates_from_api(
        professional_id, start_date.month, start_date.year
    )
    available_dates = [d["data"] for d in dates_to_check]
    logger.info(f"🔍 Datas disponíveis encontradas: {available_dates}")

    # VERIFICAÇÃO EXPLÍCITA SE A DATA PREFERIDA ESTÁ DISPONÍVEL
    if preferred_date_str and preferred_date_str != "invalid_date":
        logger.info(
            f"🔍 Verificando se data preferida {preferred_date_str} está nas datas disponíveis"
        )

        # PONTO CRÍTICO: Verificar se a data está na lista
        is_preferred_date_available = preferred_date_str in available_dates
        logger.info(f"🔍 Data preferida está disponível? {is_preferred_date_available}")

        if is_preferred_date_available:
            logger.info(f"✅ Data preferida {preferred_date_str} está disponível")
            times_raw = await api_client.get_available_times_from_api(
                professional_id, preferred_date_str
            )
            logger.info(f"🔍 Horários brutos para data preferida: {times_raw}")
            filtered_times = _filter_times_by_preference(times_raw, time_preference)
            logger.info(f"🔍 Horários filtrados para data preferida: {filtered_times}")

            if filtered_times:
                logger.info(
                    f"✅ Encontrados horários na data preferida ({preferred_date_str}): {filtered_times}"
                )
                return preferred_date_str, filtered_times, True
            else:
                logger.info(
                    f"❌ Data preferida ({preferred_date_str}) disponível, mas sem horários no turno {time_preference}"
                )
                # IMPORTANTE: Mesmo assim, retorna False para preferred_date_found
                # porque não conseguiu agendar na data preferida
        else:
            logger.info(
                f"❌ Data preferida {preferred_date_str} NÃO está nas datas disponíveis"
            )

    # Se chegou aqui, procurar a próxima data disponível
    logger.info("🔍 Procurando próxima data disponível...")
    for date_info in sorted(dates_to_check, key=lambda d: d["data"]):
        date_str = date_info["data"]
        if date_str < start_date.strftime("%Y-%m-%d"):
            logger.info(f"Pulando data passada: {date_str}")
            continue

        logger.info(f"Verificando horários para: {date_str}")
        times_raw = await api_client.get_available_times_from_api(
            professional_id, date_str
        )
        filtered_times = _filter_times_by_preference(times_raw, time_preference)

        if filtered_times:
            logger.info(
                f"✅ Encontrado o próximo dia ({date_str}) com horários "
                f"para o turno '{time_preference}': {filtered_times}"
            )
            # IMPORTANTE: Retorna False porque NÃO é a data preferida
            return date_str, filtered_times, False

    logger.warning("Nenhuma data com horários disponíveis encontrada")
    return None, [], False


def _format_date_response(
    date_formatted: str,
    professional_name: str,
    time_preference: str,
    times_str: str,
    is_requested_date: bool = False,
    unavailable_date: str = None,
) -> str:
    """Formata a mensagem de resposta com base no contexto."""
    # Dividir os horários em uma lista
    times_list = times_str.split(", ")
    
    # 🆕 LIMITE MÁXIMO: Apenas 3 horários
    times_list = times_list[:3]
    
    # Formatar cada horário em uma nova linha
    formatted_times = "\n".join(times_list)
    
    if is_requested_date:
        return (
            f"Perfeito! Para o dia {date_formatted} que você solicitou, "
            f"encontrei os seguintes horários com {professional_name} "
            f"no período da {time_preference}:\n\n{formatted_times}\n\nQual horário você prefere?"
        )
    
    # 🆕 CASO: Data não disponível, mostrando alternativa
    if unavailable_date:
        return (
            f"O dia {unavailable_date} não está disponível para consulta. "
            f"Como alternativa, encontrei os seguintes horários disponíveis com {professional_name} "
            f"para o dia {date_formatted} no período da {time_preference}:\n\n{formatted_times}\n\nQual horário você prefere?"
        )
    
    # Caso padrão
    return (
        f"Encontrei os seguintes horários disponíveis com {professional_name} "
        f"para o dia {date_formatted} no período da {time_preference}:\n\n{formatted_times}\n\nQual horário você prefere?"
    )


def _log_debug_info(
    user_requested_date: str,
    found_requested_date: bool,
    found_date: str,
    date_formatted: str,
    times_str: str,
    details: dict,
) -> None:
    """Centraliza os logs de debug em uma única função."""
    debug_info = {
        "user_requested_date": user_requested_date,
        "found_requested_date": found_requested_date,
        "found_date": found_date,
        "date_formatted": date_formatted,
        "times_str": times_str,
        "professional_name": details.professional_name,
        "time_preference": details.time_preference,
        "date_preference": details.date_preference,
    }

    for key, value in debug_info.items():
        logger.info(f"🔍 DEBUG - {key}: {value}")


def _parse_date_fallback(user_preference: str, current_date: datetime) -> Optional[str]:
    """
    Função de fallback melhorada para parsing de datas quando o LLM falhar.
    """
    if not user_preference:
        return None

    user_preference_lower = user_preference.lower().strip()
    logger.info(
        f"Fallback processando: '{user_preference}' (data atual: {current_date.strftime('%Y-%m-%d')})"
    )

    # 🆕 NOVA LÓGICA: Tratar formato DD/MM/YYYY primeiro
    import re
    
    # Regex para formato DD/MM/YYYY ou DD/MM/YY
    date_pattern = r"(\d{1,2})/(\d{1,2})/(\d{2,4})"
    date_match = re.search(date_pattern, user_preference)
    
    if date_match:
        try:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            year = int(date_match.group(3))
            
            # Se ano tem 2 dígitos, assumir 20XX
            if year < 100:
                year += 2000
            
            # Validação básica
            if not (1 <= day <= 31 and 1 <= month <= 12 and year >= current_date.year):
                logger.warning(f"Data inválida: {day}/{month}/{year}")
                return None
            
            # Criar data e retornar no formato correto
            target_date = datetime(year, month, day)
            result = target_date.strftime("%Y-%m-%d")
            logger.info(f"Fallback resultado (formato DD/MM/YYYY): {result}")
            return result
            
        except ValueError as e:
            logger.warning(f"Erro ao processar data DD/MM/YYYY: {e}")
            # Continuar para tentar outros formatos
    
    # Extrair "dia X" com regex mais robusta
    day_match = re.search(r"dia\s+(\d{1,2})", user_preference_lower)
    if day_match:
        try:
            day = int(day_match.group(1))

            # Validação básica de dia (1-31)
            if not (1 <= day <= 31):
                logger.warning(f"Dia inválido: {day}")
                return None

            current_year = current_date.year
            current_month = current_date.month
            current_day = current_date.day

            logger.info(
                f"Extraído dia: {day}, hoje é dia {current_day} de {current_month}/{current_year}"
            )

            # 🔥 LÓGICA CORRIGIDA: Se o dia ainda não chegou este mês, usar mês atual
            if day > current_day:
                logger.info(f"Dia {day} ainda não chegou este mês, usando mês atual")
                try:
                    target_date = datetime(current_year, current_month, day)
                    result = target_date.strftime("%Y-%m-%d")
                    logger.info(f"Fallback resultado (mês atual): {result}")
                    return result
                except ValueError:
                    # Dia não existe neste mês (ex: 31 de fevereiro)
                    logger.info(
                        f"Dia {day} não existe em {current_month}/{current_year}, tentando próximo mês"
                    )
                    pass

            # Se o dia já passou ou não existe neste mês, usar próximo mês
            if current_month == 12:
                next_year = current_year + 1
                next_month = 1
            else:
                next_year = current_year
                next_month = current_month + 1

            try:
                target_date = datetime(next_year, next_month, day)
                result = target_date.strftime("%Y-%m-%d")
                logger.info(f"Fallback resultado (próximo mês): {result}")
                return result
            except ValueError:
                logger.warning(f"Dia {day} não existe em {next_month}/{next_year}")
                return None

        except ValueError as e:
            logger.warning(f"Erro ao processar dia: {e}")
            return None

    # Tratar "hoje", "amanhã", etc.
    if "hoje" in user_preference_lower:
        result = current_date.strftime("%Y-%m-%d")
        logger.info(f"Fallback resultado (hoje): {result}")
        return result
    elif "amanha" in user_preference_lower or "amanhã" in user_preference_lower:
        tomorrow = current_date + timedelta(days=1)
        result = tomorrow.strftime("%Y-%m-%d")
        logger.info(f"Fallback resultado (amanhã): {result}")
        return result

    logger.warning(f"Fallback não conseguiu interpretar: '{user_preference}'")
    return None


def _validate_and_correct_translated_date(
    user_preference: str, translated_date: str, current_date: datetime
) -> str:
    """
    Valida se a data traduzida pelo LLM faz sentido e corrige se necessário.
    """
    if translated_date == "invalid_date" or not translated_date:
        return translated_date

    try:
        # Parse da data traduzida
        parsed_date = datetime.strptime(translated_date, "%Y-%m-%d")
        current_month = current_date.month
        current_day = current_date.day

        # Extrair número do dia se for formato "dia X"
        import re

        day_match = re.search(r"dia\s+(\d{1,2})", user_preference.lower())

        if day_match:
            requested_day = int(day_match.group(1))

            # Verificar se o LLM colocou no mês errado
            if (
                parsed_date.month != current_month
                and requested_day > current_day
                and requested_day <= 31
            ):  # Dia ainda não chegou este mês

                logger.warning(
                    f"🔧 CORREÇÃO: LLM traduziu 'dia {requested_day}' para "
                    f"{translated_date} (mês {parsed_date.month}), mas deveria ser mês atual ({current_month})"
                )

                # Tentar corrigir para o mês atual
                try:
                    corrected_date = datetime(
                        current_date.year, current_month, requested_day
                    )
                    corrected_str = corrected_date.strftime("%Y-%m-%d")
                    logger.info(f"🔧 Data corrigida: {corrected_str}")
                    return corrected_str
                except ValueError:
                    logger.info(
                        f"🔧 Dia {requested_day} não existe no mês {current_month}, mantendo tradução original"
                    )
                    return translated_date

        return translated_date

    except Exception as e:
        logger.warning(f"Erro ao validar data traduzida: {e}")
        return translated_date


# Adicionar detecção específica para "data mais próxima"
def _should_find_earliest_date(date_preference: str) -> bool:
    """Detecta se o usuário quer a data mais próxima disponível."""
    if not date_preference:
        return False
        
    earliest_keywords = [
        "mais próxima", "mais proxima", "a mais próxima", "a mais proxima",
        "primeira disponível", "primeira data", "qualquer data",
        "quanto antes", "o mais breve", "breve possível"
    ]
    
    return any(keyword in date_preference.lower() for keyword in earliest_keywords)


# --- O Nó Principal (VERSÃO ATUALIZADA) ---


async def check_availability_node(
    state: MessageAgentState,
) -> MessageAgentState:
    logger.info("--- Executando nó check_availability (Versão Robusta 5.0) ---")
    current_messages = state.get("messages", [])
    details = state.get("extracted_scheduling_details")

    try:
        if not details:
            raise ValueError("Detalhes do agendamento não encontrados no estado.")

        api_client = AppHealthAPIClient()
        repository = AppHealthAPIMedicalRepository(api_client)
        llm_service = LLMFactory.create_llm_service("openai")

        if not (
            professional_id := await _get_professional_id_by_name(
                details.professional_name, repository
            )
        ):
            raise ValueError(
                f"Cadastro do profissional '{details.professional_name}' "
                f"não encontrado."
            )

        today = datetime.now()
        logger.info(f"Data atual: {today.strftime('%Y-%m-%d')}")
        logger.info(f"Preferência do usuário: '{details.date_preference}'")

        # TENTATIVA 1: Usar o LLM para traduzir a data
        translated_date = llm_service.translate_natural_date(
            user_preference=details.date_preference,
            current_date=today.strftime("%Y-%m-%d"),
        )
        logger.info(f"🔍 DEBUG - Data traduzida pelo LLM: '{translated_date}'")

        # 🆕 TENTATIVA 1.5: Validar e corrigir a tradução do LLM se necessário
        if translated_date != "invalid_date":
            corrected_date = _validate_and_correct_translated_date(
                details.date_preference, translated_date, today
            )
            if corrected_date != translated_date:
                logger.info(
                    f"🔧 Data corrigida de '{translated_date}' para '{corrected_date}'"
                )
                translated_date = corrected_date

        # TENTATIVA 2: Se o LLM falhar, usar função de fallback
        if translated_date == "invalid_date":
            logger.warning("LLM falhou na tradução. Usando função de fallback...")
            translated_date = _parse_date_fallback(details.date_preference, today)
            logger.info(f"🔍 DEBUG - Data traduzida por fallback: '{translated_date}'")

        # VERIFICAÇÃO EXPLÍCITA DE DATA ESPECÍFICA
        SPECIFIC_DATE_KEYWORDS = ["dia", "hoje", "amanhã", "/"]
        user_asked_specific_day = any(
            word in (details.date_preference or "").lower() for word in SPECIFIC_DATE_KEYWORDS
        )
        logger.info(
            f"🔍 DEBUG - Usuário pediu data específica? {user_asked_specific_day}"
        )

        # 🔧 DETECÇÃO ESPECÍFICA: Data mais próxima
        if _should_find_earliest_date(details.date_preference):
            logger.info(f"🎯 Usuário quer data mais próxima: '{details.date_preference}'")
            # Forçar busca pela primeira data disponível
            result = await _find_first_available_slot(
                api_client,
                professional_id,
                details.time_preference,
                today,
                None,  # 🔧 None para buscar primeira disponível
            )
        else:
            # Lógica existente para datas específicas
            result = await _find_first_available_slot(
                api_client,
                professional_id,
                details.time_preference,
                today,
                translated_date,
            )
        logger.info(f"🔍 DEBUG - Resultado completo da busca: {result}")

        # 🔧 CORREÇÃO: Verificação mais robusta do resultado
        if result and len(result) == 3:
            found_date, suggested_times, preferred_date_found = result
            
            # ✅ Verificação adicional se realmente encontrou algo
            if found_date and suggested_times:
                logger.info(f"✅ Encontrou horários: data={found_date}, horários={len(suggested_times)}")
                
                times_str = ", ".join([t[:5] for t in suggested_times])
                date_formatted = datetime.strptime(found_date, "%Y-%m-%d").strftime("%d/%m/%Y")

                # LOGS DE DEBUG CRÍTICOS
                logger.info(f"🔍 DEBUG CRÍTICO - found_date: {found_date}")
                logger.info(f"🔍 DEBUG CRÍTICO - preferred_date_found: {preferred_date_found}")
                logger.info(f"🔍 DEBUG CRÍTICO - translated_date: {translated_date}")
                logger.info(f"🔍 DEBUG CRÍTICO - user_asked_specific_day: {user_asked_specific_day}")

                # CONDIÇÕES EXPLÍCITAS PARA DEBUG
                condition_1 = preferred_date_found
                condition_2 = user_asked_specific_day and translated_date is not None

                logger.info(f"🔍 DEBUG CONDIÇÕES:")
                logger.info(f"    - Condição 1 (data preferida encontrada): {condition_1}")
                logger.info(f"    - Condição 2 (data específica + traduzida): {condition_2}")

                # 🆕 CORREÇÃO CRÍTICA: Verificar se a data encontrada É a data que o usuário pediu
                # Mesmo que preferred_date_found seja False, se as datas coincidem, não dizer que está indisponível
                user_requested_date_matches = False
                if translated_date and found_date:
                    user_requested_date_matches = (translated_date == found_date)
                    logger.info(f"🔍 DEBUG CRÍTICO - Datas coincidem? translated_date='{translated_date}' vs found_date='{found_date}' -> {user_requested_date_matches}")
                
                # 🆕 VERIFICAÇÃO EXTRA: Comparar também com a data original do usuário
                user_date_also_matches = False
                if details.date_preference and found_date:
                    # Tentar converter a data do usuário para o formato correto para comparação
                    try:
                        # Se está no formato DD/MM/YYYY, converter para YYYY-MM-DD
                        if "/" in details.date_preference:
                            parts = details.date_preference.split("/")
                            if len(parts) == 3:
                                day, month, year = parts
                                user_date_formatted = f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
                                user_date_also_matches = (user_date_formatted == found_date)
                                logger.info(f"🔍 DEBUG EXTRA - Data original do usuário '{details.date_preference}' convertida para '{user_date_formatted}' vs found_date='{found_date}' -> {user_date_also_matches}")
                    except Exception as e:
                        logger.warning(f"Erro na verificação extra de data: {e}")

                if condition_1 or user_requested_date_matches or user_date_also_matches:  # 🔧 ADICIONADAS AS CONDIÇÕES DE MATCH
                    logger.info("🟢 FLUXO: Data preferida encontrada OU data coincide - resposta positiva")
                    response_text = _format_date_response(
                        date_formatted,
                        details.professional_name,
                        details.time_preference,
                        times_str,
                        is_requested_date=True,
                    )
                else:
                    logger.info("🔵 FLUXO: Próxima data disponível encontrada (diferente da solicitada)")
                    
                    # 🆕 EXTRAIR DIA DA DATA PREFERIDA PARA MENSAGEM
                    user_date_formatted = None
                    if user_asked_specific_day and details.date_preference:
                        user_date_formatted = details.date_preference.replace("dia", "").strip()
                    
                    response_text = _format_date_response(
                        date_formatted,
                        details.professional_name,
                        details.time_preference,
                        times_str,
                        unavailable_date=user_date_formatted,  # 🆕 PASSAR DATA NÃO DISPONÍVEL
                    )

                return {
                    **state,
                    "messages": current_messages + [AIMessage(content=response_text)],
                    "conversation_context": "awaiting_slot_selection",
                    "next_step": "completed",
                }
            else:
                logger.info("🔴 result existe mas sem dados válidos - tratando como data não encontrada")
        
        # 🆕 FLUXO QUANDO NÃO ENCONTRA NADA OU DATA ESPECÍFICA INDISPONÍVEL
        logger.info("🔴 Nenhuma data com horários encontrada - buscando alternativas")
        
        # Se usuário pediu data específica, mostrar alternativas
        if user_asked_specific_day and translated_date:
            logger.info("🟠 Data específica não disponível - mostrando alternativas")
            
            try:
                # 🔧 BUSCAR DATAS DISPONÍVEIS COM FILTRAGEM POR TURNO
                dates_to_check = await api_client.get_available_dates_from_api(
                    professional_id, today.month, today.year
                )
                
                # 🆕 FILTRAR POR TURNO
                dates_with_matching_period = []
                
                for date_info in dates_to_check:
                    date_str = date_info["data"]
                    
                    # Pular datas passadas
                    if date_str < today.strftime("%Y-%m-%d"):
                        continue
                    
                    # Verificar se esta data tem horários no turno solicitado
                    try:
                        times_raw = await api_client.get_available_times_from_api(
                            professional_id, date_str
                        )
                        
                        # Verificar se tem horários no período solicitado
                        has_matching_period = False
                        for slot in times_raw:
                            start_hour = int(slot["horaInicio"].split(":")[0])
                            if details.time_preference == "manha" and 5 <= start_hour < 12:
                                has_matching_period = True
                                break
                            elif details.time_preference == "tarde" and 12 <= start_hour < 18:
                                has_matching_period = True
                                break
                        
                        if has_matching_period:
                            dates_with_matching_period.append(date_str)
                            
                    except Exception as e:
                        logger.warning(f"Erro ao verificar horários para {date_str}: {e}")
                        continue

                # Verificar se encontrou datas com o turno solicitado
                if not dates_with_matching_period:
                    user_date_formatted = details.date_preference.replace("dia", "").strip()
                    response_text = (
                        f"O dia {user_date_formatted} que você solicitou não possui horários disponíveis "
                        f"para {details.professional_name} no período da {details.time_preference}.\n\n"
                        f"Infelizmente, não encontrei outras datas disponíveis no período da {details.time_preference} "
                        f"neste mês. Gostaria de verificar outro turno ou o próximo mês?"
                    )
                else:
                    # 🆕 FORMATAR APENAS AS DATAS COM O TURNO CORRETO
                    formatted_dates = []
                    for date_str in dates_with_matching_period[:6]:  # Mostrar até 6 datas
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        formatted_dates.append(date_obj.strftime("%d/%m"))

                    formatted_dates_str = ", ".join(formatted_dates)
                    user_date_formatted = details.date_preference.replace("dia", "").strip()

                    response_text = (
                        f"O dia {user_date_formatted} que você solicitou não possui horários disponíveis "
                        f"para {details.professional_name} no período da {details.time_preference}.\n\n"
                        f"Datas disponíveis no período da {details.time_preference}: {formatted_dates_str}\n\n"
                        f"Qual data você prefere?"
                    )

                return {
                    **state,
                    "messages": current_messages + [AIMessage(content=response_text)],
                    "conversation_context": "awaiting_date_selection",
                    "next_step": "completed",
                }
                
            except Exception as inner_e:
                logger.error(f"Erro ao buscar datas alternativas: {inner_e}")
                response_text = (
                    f"O dia {details.date_preference} não está disponível, mas tive "
                    f"dificuldade para buscar outras opções. Poderia tentar uma data diferente?"
                )
                return {
                    **state,
                    "messages": current_messages + [AIMessage(content=response_text)],
                    "next_step": "completed",
                }
        
        # 🔧 CORREÇÃO: Resposta quando não encontra horários (sem "próximo mês")
        response_text = (
            f"Puxa, parece que o(a) {details.professional_name} não possui "
            f"horários disponíveis no período da {details.time_preference} "
            f"para este mês. Gostaria de tentar outro turno?"
        )
        return {
            **state,
            "messages": current_messages + [AIMessage(content=response_text)],
            "conversation_context": "awaiting_time_shift",  # 🔧 CONTEXTO ESPECÍFICO
            "next_step": "completed",
        }

    except Exception as e:
        logger.error(
            f"Erro crítico inesperado no nó check_availability: {e}",
            exc_info=True,
        )
        error_message = AIMessage(
            content="Desculpe, tive uma dificuldade em consultar a agenda. "
            "Poderia tentar novamente em alguns instantes?"
        )
        return {
            **state,
            "messages": current_messages + [error_message],
            "next_step": "completed",
        }
