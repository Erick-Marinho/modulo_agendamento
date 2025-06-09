from langchain_openai import ChatOpenAI
from app.application.agents.prompts.classify_message_prompt import (
    CLASSIFY_MESSAGE_TEMPLATE,
)
from app.application.agents.prompts.extract_scheduling_details_prompt import (
    EXTRACT_SCHEDULING_DETAILS_TEMPLATE,
)
from app.application.agents.prompts.request_missing_info_prompt import (
    REQUEST_MISSING_INFO_TEMPLATE,
)
from app.application.agents.prompts.generate_confirmation_prompt import (
    GENERATE_CONFIRMATION_TEMPLATE,
)
from app.application.agents.prompts.generate_success_message_prompt import (
    GENERATE_SUCCESS_MESSAGE_TEMPLATE,
)
from app.application.agents.prompts.generate_correction_request_prompt import (
    GENERATE_CORRECTION_REQUEST_TEMPLATE,
)
from app.application.agents.prompts.generate_general_help_prompt import (
    GENERATE_GENERAL_HELP_TEMPLATE,
)
from app.application.agents.prompts.classify_confirmation_response_prompt import (
    CLASSIFY_CONFIRMATION_RESPONSE_TEMPLATE,
)
from app.application.agents.prompts.translate_date_prompt import TRANSLATE_DATE_PROMPT
from app.application.interfaces.illm_service import ILLMService
from app.domain.sheduling_details import SchedulingDetails
from langchain_core.output_parsers import PydanticOutputParser
from typing import Optional, List
from app.infrastructure.config.config import settings
import logging
import re

logger = logging.getLogger(__name__)


class OpenAIService(ILLMService):
    def __init__(self) -> None:
        self.client = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL_NAME,
            temperature=settings.OPENAI_TEMPERATURE,
        )

    def classify_message(self, user_message: str) -> str:
        """
        Classifica a mensagem do usuário em uma das categorias:
        - "agendamento"
        - "cancelamento"
        - "reagendamento"
        - "outro"

        """
        chain = CLASSIFY_MESSAGE_TEMPLATE | self.client
        try:
            llm_response = chain.invoke({"user_query": user_message})
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao classificar mensagem: {e}")
            return None

    def extract_scheduling_details(
        self, user_message: str
    ) -> Optional[SchedulingDetails]:
        parser = PydanticOutputParser(pydantic_object=SchedulingDetails)
        chain = EXTRACT_SCHEDULING_DETAILS_TEMPLATE | self.client | parser
        try:
            extract_data = chain.invoke({"conversation_history": user_message})
            return extract_data
        except Exception as e:
            logger.error(f"Erro ao extrair detalhes do agendamento: {e}")
            return None

    def generate_clarification_question(
        self,
        service_type: str,
        missing_fields_list: str,
        professional_name: Optional[str],
        specialty: Optional[str],
        date_preference: Optional[str],
        time_preference: Optional[str],
    ) -> str:
        """
        Gera uma pergunta para o usuário solicitando informações de agendamento faltantes.

        Args:
            service_type: O tipo de serviço que o usuário deseja agendar.
            missing_fields_list: Uma string formatada listando os campos que estão faltando.
            professional_name: Nome do profissional já coletado.
            specialty: Especialidade já coletada.
            date_preference: Preferência de data já coletada.
        """
        prompt_values = {
            "service_type": service_type or "serviço não especificado",
            "missing_fields_list": missing_fields_list,
            "professional_name": professional_name or "Não informado",
            "specialty": specialty or "Não informada",
            "date_preference": date_preference or "Não informada",
            "time_preference": time_preference or "Não informado",
        }

        chain = REQUEST_MISSING_INFO_TEMPLATE | self.client
        try:
            llm_response = chain.invoke(prompt_values)
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar pergunta de esclarecimento: {e}")
            return None

    def generate_confirmation_message(self, details: SchedulingDetails) -> str:
        """
        Gera uma mensagem de confirmação dos dados de agendamento.
        """
        prompt_values = {
            "professional_name": details.professional_name or "Não especificado",
            "specialty": details.specialty or "Não especificada",
            "date_preference": details.date_preference or "Não especificada",
            "time_preference": details.time_preference or "Não especificado",
            "service_type": details.service_type or "Não especificado",
        }

        chain = GENERATE_CONFIRMATION_TEMPLATE | self.client
        try:
            llm_response = chain.invoke(prompt_values)
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de confirmação: {e}")
            return None

    def generate_success_message(self) -> str:
        """
        Gera uma mensagem de sucesso após confirmação do agendamento.
        """
        chain = GENERATE_SUCCESS_MESSAGE_TEMPLATE | self.client
        try:
            llm_response = chain.invoke({})
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de sucesso: {e}")
            return "Dados confirmados com sucesso!"

    def generate_correction_request_message(self) -> str:
        """
        Gera uma mensagem solicitando correção de dados.
        """
        chain = GENERATE_CORRECTION_REQUEST_TEMPLATE | self.client
        try:
            llm_response = chain.invoke({})
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de correção: {e}")
            return "Me informe o que gostaria de alterar."

    def generate_general_help_message(self) -> str:
        """
        Gera uma mensagem de ajuda geral sobre a clínica.
        """
        chain = GENERATE_GENERAL_HELP_TEMPLATE | self.client
        try:
            llm_response = chain.invoke({})
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de ajuda: {e}")
            return (
                "Posso ajudar com agendamentos. Informe profissional, data e horário."
            )

    def generate_unclear_response_message(self) -> str:
        """
        Gera uma mensagem quando a resposta do usuário não é clara.
        """
        # Prompt simples
        prompt = "Gere uma pergunta curta e amigável pedindo confirmação: 'sim' ou 'não' para agendamento. Seja natural e conciso."
        try:
            llm_response = self.client.invoke(prompt)
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de esclarecimento: {e}")
            return "Confirma os dados? Responda 'sim' ou 'não'."

    def generate_greeting_message(self) -> str:
        """
        Gera uma mensagem de saudação.
        """
        prompt = "Gere uma saudação amigável e profissional para assistente de agendamento médico. Seja conciso."
        try:
            llm_response = self.client.invoke(prompt)
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar saudação: {e}")
            return "Olá! Como posso ajudar você?"

    def generate_farewell_message(self) -> str:
        """
        Gera uma mensagem de despedida.
        """
        prompt = "Gere uma despedida amigável e profissional. Seja conciso e natural."
        try:
            llm_response = self.client.invoke(prompt)
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar despedida: {e}")
            return "Até mais! Tenha um ótimo dia!"

    def generate_fallback_message(self) -> str:
        """
        Gera uma mensagem quando não entende o usuário.
        """
        prompt = "Gere uma mensagem amigável quando não entender o que o usuário disse. Peça para tentar novamente. Seja conciso."
        try:
            llm_response = self.client.invoke(prompt)
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de fallback: {e}")
            return "Não entendi bem. Pode tentar novamente?"

    def generate_confirmation_message(self, details: SchedulingDetails) -> str:
        """
        Gera uma mensagem de confirmação dos dados de agendamento.
        """
        prompt_values = {
            "professional_name": details.professional_name or "Não especificado",
            "specialty": details.specialty or "Não especificada",
            "date_preference": details.date_preference or "Não especificada",
            "time_preference": details.time_preference or "Não especificado",
            "service_type": details.service_type or "Não especificado",
        }

        chain = GENERATE_CONFIRMATION_TEMPLATE | self.client
        try:
            llm_response = chain.invoke(prompt_values)
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de confirmação: {e}")
            return None

    def classify_confirmation_response(self, user_response: str) -> str:
        """
        Classifica a resposta do usuário sobre confirmação de agendamento.
        """
        chain = CLASSIFY_CONFIRMATION_RESPONSE_TEMPLATE | self.client
        try:
            llm_response = chain.invoke({"user_response": user_response})
            classification = llm_response.content.strip().lower()

            valid_categories = [
                "confirmed",
                "simple_rejection",
                "correction_with_data",
                "unclear",
            ]
            if classification in valid_categories:
                logger.info(
                    f"Classificação válida: '{classification}' para '{user_response}'"
                )
                return classification
            else:
                logger.warning(
                    f"Classificação inválida do LLM: '{classification}'. Usando fallback."
                )
                return "unclear"

        except Exception as e:
            logger.error(f"Erro ao classificar resposta de confirmação: {e}")
            return "unclear"

    def translate_natural_date(self, user_preference: str, current_date: str) -> str:
        """
        Traduz a data natural do usuário usando o LLM.
        """
        chain = TRANSLATE_DATE_PROMPT | self.client
        try:
            prompt_values = {
                "current_date": current_date,
                "user_preference": user_preference,
            }
            llm_response = chain.invoke(prompt_values)
            translated_date = llm_response.content.strip()

            # Validação simples de formato (YYYY-MM-DD) ou a string de erro
            if (
                re.match(r"^\d{4}-\d{2}-\d{2}$", translated_date)
                or translated_date == "invalid_date"
            ):
                logger.info(
                    f"LLM traduziu '{user_preference}' para '{translated_date}'"
                )
                return translated_date

            logger.warning(
                f"LLM retornou formato de data inesperado: '{translated_date}'"
            )
            return "invalid_date"

        except Exception as e:
            logger.error(f"Erro ao traduzir data natural: {e}")
            return "invalid_date"
