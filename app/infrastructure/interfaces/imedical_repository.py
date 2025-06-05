from abc import ABC, abstractmethod
from typing import List
from app.domain.entities.medical_specialty import ApiMedicalSpecialty
from app.domain.entities.medical_professional import ApiMedicalProfessional

class IMedicalRepository(ABC):
    """
    Interface para repositório de especialidades e profissionais médicos.
    """

    @abstractmethod
    async def get_all_api_specialties(self) -> List[ApiMedicalSpecialty]:
        """Retorna todas as especialidades médicas disponíveis da API."""
        pass

    @abstractmethod
    async def get_api_professionals(self) -> List[ApiMedicalProfessional]:
        """Retorna todos os profissionais (ativos) da API."""
        pass

    @abstractmethod
    async def get_professionals_by_specialty_name(self, specialty_name: str) -> List[ApiMedicalProfessional]:
        """
        Retorna profissionais de uma especialidade específica, filtrando os resultados da API.
        """
        pass
