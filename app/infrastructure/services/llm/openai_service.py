from langchain_openai import ChatOpenAI
from app.application.agents.prompts.analyze_user_intent_prompt import ANALYZE_USER_INTENT_TEMPLATE
from app.application.agents.prompts.classify_message_prompt import CLASSIFY_MESSAGE_TEMPLATE
from app.application.agents.prompts.extract_scheduling_details_prompt import EXTRACT_SCHEDULING_DETAILS_TEMPLATE
from app.application.agents.prompts.request_missing_info_prompt import REQUEST_MISSING_INFO_TEMPLATE
from app.application.agents.prompts.scheduling_validation_prompt import SCHEDULING_VALIDATION_TEMPLATE
from app.application.interfaces.illm_service import ILLMService
from app.domain.sheduling_details import SchedulingDetails
from langchain_core.output_parsers import PydanticOutputParser
from typing import Optional
from app.infrastructure.config.config import settings
import logging

logger = logging.getLogger(__name__)

class OpenAIService(ILLMService):
    def __init__(self) -> None:
        self.client = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL_NAME,
            temperature=settings.OPENAI_TEMPERATURE
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

    def extract_scheduling_details(self, user_message: str) -> Optional[SchedulingDetails]:
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
        
    def analyze_user_intent(self, conversation_history, user_message: str, existing_scheduling_details: Optional[SchedulingDetails]) -> str:
        """
        Analisa a intenção do usuário com base na conversa e na mensagem atual.

        Args:
            conversation_history: Histórico da conversa até o momento.
            user_message: Mensagem do usuário.

        Returns:
            Uma string indicando a intenção do usuário:
            - CREATE/READ/UPDATE/CANCEL/UNCLEAR
        """
        try:
            chain = ANALYZE_USER_INTENT_TEMPLATE | self.client
            
            llm_response = chain.invoke({
                "conversation_history": conversation_history,
                "existing_scheduling_details": existing_scheduling_details,
                "current_message": user_message
            })

            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao analisar intenção do usuário: {e}")
            return None
        

    def validate_scheduling_user_confirmation(self, user_message: str):
        
        """
        Analisa a resposta do usuário para determinar se ele confirma ou deseja alterar os dados do agendamento.

        Args:
            user_message: A mensagem do usuário em resposta à solicitação de confirmação.

        Returns:
            Uma string JSON indicando a intenção do usuário:
            - "CONFIRMED_SCHEDULING_DATA" se o usuário confirma os dados
            - "ALTER_SCHEDULING_DATA" se o usuário deseja fazer alterações sem especificar quais
            - "ALTER_SPECIFIC_SCHEDULING_DATA" se o usuário deseja fazer alterações especificando e passando novos valores
            - "UNCLEAR" se a intenção não está clara
        """
        try:
            chain = SCHEDULING_VALIDATION_TEMPLATE | self.client
            llm_response = chain.invoke({"user_query": user_message})

            
            return llm_response.content
        except Exception as e:
            logger.error(f"Erro ao validar confirmação do agendamento: {e}")
            # return '{"intent": "UNCLEAR", "change_details": {}}'
            return None
