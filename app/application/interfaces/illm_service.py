from abc import ABC, abstractmethod
from app.domain.sheduling_details import SchedulingDetails
from typing import Optional, List


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
    def extract_scheduling_details(
        self, user_message: str
    ) -> Optional[SchedulingDetails]:
        """
        Extrai os detalhes de agendamento da mensagem do usuário.

        Args:
            user_message: A mensagem do usuário contendo os detalhes de agendamento.

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
    def generate_confirmation_message(self, details: SchedulingDetails) -> str:
        """
        Gera uma mensagem de confirmação dos dados de agendamento.

        Args:
            details: Detalhes do agendamento coletados.

        Returns:
            Mensagem de confirmação formatada.
        """
        pass

    @abstractmethod
    def generate_success_message(self) -> str:
        """
        Gera uma mensagem de sucesso após confirmação do agendamento.

        Returns:
            Mensagem de sucesso humanizada.
        """
        pass

    @abstractmethod
    def generate_correction_request_message(self) -> str:
        """
        Gera uma mensagem solicitando correção de dados.

        Returns:
            Mensagem para solicitar correções.
        """
        pass

    @abstractmethod
    def generate_unclear_response_message(self) -> str:
        """
        Gera uma mensagem quando a resposta do usuário não é clara.

        Returns:
            Mensagem de esclarecimento.
        """
        pass

    @abstractmethod
    def generate_general_help_message(self) -> str:
        """
        Gera uma mensagem de ajuda geral sobre a clínica.

        Returns:
            Mensagem de ajuda humanizada.
        """
        pass

    @abstractmethod
    def generate_greeting_message(self) -> str:
        """
        Gera uma mensagem de saudação.

        Returns:
            Mensagem de saudação humanizada.
        """
        pass

    @abstractmethod
    def generate_farewell_message(self) -> str:
        """
        Gera uma mensagem de despedida.

        Returns:
            Mensagem de despedida humanizada.
        """
        pass

    @abstractmethod
    def generate_fallback_message(self) -> str:
        """
        Gera uma mensagem quando não entende o usuário.

        Returns:
            Mensagem de fallback humanizada.
        """
        pass

    @abstractmethod
    def generate_confirmation_message(self, details: SchedulingDetails) -> str:
        """
        Gera uma mensagem de confirmação dos dados de agendamento.

        Args:
            details: Detalhes do agendamento coletados.

        Returns:
            Mensagem de confirmação formatada.
        """
        pass

    @abstractmethod
    def classify_confirmation_response(self, user_response: str) -> str:
        """
        Classifica a resposta do usuário sobre confirmação de agendamento.

        Args:
            user_response: Resposta do usuário à pergunta de confirmação

        Returns:
            Categoria: "confirmed", "simple_rejection", "correction_with_data", ou "unclear"
        """
        pass

    @abstractmethod
    def translate_natural_date(self, user_preference: str, current_date: str) -> str:
        """
        Traduz uma preferência de data em linguagem natural para uma data concreta
        baseada em uma lista de datas disponíveis.
        """
        pass
