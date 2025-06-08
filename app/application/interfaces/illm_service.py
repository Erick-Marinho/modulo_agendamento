from abc import ABC, abstractmethod
from app.domain.sheduling_details import SchedulingDetails
from typing import Optional

class ILLMService(ABC):
    """Interface base para serviço de LLM"""

    @abstractmethod
    def classify_message(self, message: str) -> str:
        """
        Classifica a mensagem do usuário em uma categoria de agendamento.

        Args:
            message: A mensagem do usuário contendo os detalhes de agendamento.

        Returns:
            A categoria da mensagem.
        """
        pass

    @abstractmethod
    def extract_scheduling_details(self, conversation_history: str) -> Optional[SchedulingDetails]:
        """
        Extrai os detalhes de agendamento da mensagem do usuário.

        Args:
            conversation_history: A mensagem do usuário contendo os detalhes de agendamento.

        Returns:
        """
        pass

    @abstractmethod
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
            time_preference: Preferência de horário já coletada.

        Returns:
            A pergunta gerada pelo LLM para ser enviada ao usuário.
        """
        pass

    @abstractmethod
    def analyze_user_intent(self, conversation_history, user_message: str) -> str:
        """
        Analisa a intenção do usuário com base na conversa e na mensagem atual.

        Args:
            conversation_history: Histórico da conversa até o momento.
            user_message: Mensagem do usuário.

        Returns:
            Uma string indicando a intenção do usuário:
            - CREATE: Se o usuario quiser criar um novo agendamento
            - UPDATE: Se o usuario quiser alterar um agendamento existente
            - UNCLEAR: Se a intenção não está clara
        """
        pass

    @abstractmethod
    def update_scheduling_datails(self, scheduling_details: SchedulingDetails, user_message: str) -> SchedulingDetails:
        """
        Atualiza os dados do agendamento com base na mensagem do usuário.
        """
        pass

    @abstractmethod
    def classification_confirmation_response(self, user_message: str) -> str:
        """
        Classifica a resposta do usuário como confirmação ou não
        """
        pass

    @abstractmethod
    def generate_success_message(self) -> str:
        """
        Gera uma mensagem de sucesso para o usuário.
        """
        pass
    
    @abstractmethod
    def generate_correction_request_message(self) -> str:
        """
        Gera uma mensagem de solicitação de correção para o usuário.
        """
        pass

    @abstractmethod
    def generate_confirmation_message(self, details: SchedulingDetails) -> str:
        """
        Gera uma mensagem de confirmação dos dados de agendamento.
        """
        pass
    
    
    @abstractmethod
    def validate_scheduling_user_confirmation(self, user_message: str) -> str:
        """
        Analisa a resposta do usuário para determinar se ele confirma ou deseja alterar os dados do agendamento.

        Args:
            user_message: A mensagem do usuário em resposta à solicitação de confirmação.

        Returns:
            Uma string indicando a intenção do usuário:
            - "CONFIRMED_SCHEDULING_DATA" se o usuário confirma os dados
            - "ALTER_SCHEDULING_DATA" se o usuário deseja fazer alterações sem especificar quais
            - "ALTER_SPECIFIC_SCHEDULING_DATA" se o usuário deseja fazer alterações especificando e passando novos valores
            - "UNCLEAR" se a intenção não está clara
        """
        pass
  