import logging
from typing import List
from app.infrastructure.interfaces.imedical_repository import IMedicalRepository
from app.domain.entities.medical_specialty import ApiMedicalSpecialty
from app.domain.entities.medical_professional import ApiMedicalProfessional
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient

logger = logging.getLogger(__name__)


class AppHealthAPIMedicalRepository(IMedicalRepository):
    """
    Implementação do repositório para especialidades e profissionais médicos.
    """

    def __init__(self, api_client: AppHealthAPIClient):
        """
        Inicializa o repositório com o cliente HTTP da API.
        """
        self._api_client = api_client

    async def get_all_api_specialties(self) -> List[ApiMedicalSpecialty]:
        """Retorna todas as especialidades médicas disponíveis da API."""
        try:
            logger.info("Repository: Fetching all API specialties.")
            specialties = await self._api_client.get_specialties_from_api()
            return specialties
        except Exception as e:
            logger.error(f"Repository: Error fetching API specialties: {e}")
            return []

    async def get_api_professionals(self) -> List[ApiMedicalProfessional]:
        """Retorna todos os profissionais (ativos) da API."""
        try:
            logger.info("Repository: Fetching all API professionals.")
            professionals = await self._api_client.get_professionals_from_api()
            return professionals
        except Exception as e:
            logger.error(f"Repository: Error fetching API professionals: {e}")
            return []

    async def get_professionals_by_specialty_name(
        self, specialty_name: str
    ) -> List[ApiMedicalProfessional]:
        """
        Retorna profissionais de uma especialidade específica, filtrando os resultados da API.
        """
        try:
            logger.info(
                f"Repository: Fetching professionals for specialty: {specialty_name}"
            )
            all_professionals = await self.get_api_professionals()

            if not all_professionals:
                return []

            filtered_professionals: List[ApiMedicalProfessional] = []
            for prof in all_professionals:
                for spec_link in prof.especialidades:
                    if (
                        spec_link.especialidade.strip().lower()
                        == specialty_name.strip().lower()
                    ):
                        filtered_professionals.append(prof)
                        break

            logger.info(
                f"Repository: Found {len(filtered_professionals)} professionals for specialty '{specialty_name}'."
            )
            return filtered_professionals
        except Exception as e:
            logger.error(
                f"Repository: Error fetching professionals by specialty name '{specialty_name}': {e}"
            )
            return []


if __name__ == "__main__":
    import asyncio

    async def main():
        api_client = AppHealthAPIClient()
        repository = AppHealthAPIMedicalRepository(api_client=api_client)

        print("Buscando todas as especialidades via repositório...")
        specialties = await repository.get_all_api_specialties()
        if specialties:
            for spec in specialties:
                print(f"- ID: {spec.id}, Especialidade: {spec.especialidade}")
        else:
            print("Nenhuma especialidade encontrada ou erro na busca.")

        print("\nBuscando todos os profissionais via repositório...")
        professionals = await repository.get_api_professionals()
        if professionals:
            print(f"Total de {len(professionals)} profissionais encontrados.")
            # for prof in professionals:
            #     print(f"- ID: {prof.id}, Nome: {prof.nome}")
        else:
            print("Nenhum profissional encontrado ou erro na busca.")

        print("\nBuscando profissionais de 'Cardiologia' via repositório...")
        cardio_professionals = await repository.get_professionals_by_specialty_name(
            "Cardiologia"
        )
        if cardio_professionals:
            for prof in cardio_professionals:
                print(f"- ID: {prof.id}, Nome: {prof.nome}")
                for spec_link in prof.especialidades:
                    if spec_link.especialidade.lower() == "cardiologia":
                        print(f"  -> Atende em: {spec_link.especialidade}")
        else:
            print("Nenhum profissional de Cardiologia encontrado.")

        print("\nBuscando profissionais de 'Clínico Geral' via repositório...")
        clinico_professionals = await repository.get_professionals_by_specialty_name(
            "Clínico Geral"
        )
        if clinico_professionals:
            for prof in clinico_professionals:
                print(f"- ID: {prof.id}, Nome: {prof.nome}")
                for spec_link in prof.especialidades:
                    if spec_link.especialidade.lower() == "clínico geral":
                        print(f"  -> Atende em: {spec_link.especialidade}")
        else:
            print("Nenhum profissional de Clínico Geral encontrado.")

    asyncio.run(main())
