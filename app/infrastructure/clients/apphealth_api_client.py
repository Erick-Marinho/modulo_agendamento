import httpx
import logging
from typing import List, Optional, Any, Dict
from app.infrastructure.config.config import settings
from app.domain.entities.medical_specialty import ApiMedicalSpecialty
from app.domain.entities.medical_professional import ApiMedicalProfessional

logger = logging.getLogger(__name__)

class AppHealthAPIClient:
    def __init__(self):
        self.base_url = settings.APPHEALTH_API_BASE_URL
        self.headers = {
            "Authorization": settings.APPHEALTH_API_TOKEN
        }

    async def _request(self, method: str, endpoint: str, params: Optional[dict] = None) -> Any:
        """Método genérico para realizar requisições HTTP."""
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                logger.debug(f"Requesting URL: {url} with params: {params}")
                response = await client.request(method, url, headers=self.headers, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text} for URL: {url}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error occurred: {e} for URL: {url}")
                raise
            except Exception as e:
                logger.error(f"An unexpected error occurred during API request: {e} for URL: {url}")
                raise

    async def get_specialties_from_api(self) -> List[ApiMedicalSpecialty]:
        """Busca todas as especialidades da API AppHealth."""
        try:
            logger.info("Fetching specialties from AppHealth API")
            data = await self._request("GET", "/especialidades")
            specialties = [ApiMedicalSpecialty(**item) for item in data]
            logger.info(f"Successfully fetched {len(specialties)} specialties.")
            return specialties
        except Exception as e:
            logger.error(f"Failed to fetch or parse specialties: {e}")
            return []

    async def get_professionals_from_api(self) -> List[ApiMedicalProfessional]:
        """Busca todos os profissionais (com status=true) da API AppHealth."""
        try:
            logger.info("Fetching professionals from AppHealth API")
            data = await self._request("GET", "/profissionais", params={"status": "true"})
            professionals = [ApiMedicalProfessional(**item) for item in data]
            logger.info(f"Successfully fetched {len(professionals)} professionals.")
            return professionals
        except Exception as e:
            logger.error(f"Failed to fetch or parse professionals: {e}")
            return []
        
    async def get_available_dates_from_api(self, professional_id: int, month: int, year: int) -> List[Dict[str, Any]]:
        """Busca as datas disponíveis para um profissional em um mês/ano específico."""
        try:
            endpoint = f"/agenda/profissionais/{professional_id}/datas"
            params = {"mes": str(month), "ano": str(year)}
            logger.info(f"Fetching available dates from {endpoint} with params {params}")
            data = await self._request("GET", endpoint, params=params)
            logger.info(f"Successfully fetched {len(data)} available dates for professional {professional_id}.")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch or parse available dates for professional {professional_id}: {e}")
            return []

    async def get_available_times_from_api(self, professional_id: int, date: str) -> List[Dict[str, Any]]:
        """Busca os horários disponíveis para um profissional em uma data específica."""
        try:
            endpoint = f"/agenda/profissionais/{professional_id}/horarios"
            params = {"data": date}
            logger.info(f"Fetching available times from {endpoint} with params {params}")
            data = await self._request("GET", endpoint, params=params)
            logger.info(f"Successfully fetched {len(data)} available time slots for professional {professional_id} on {date}.")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch or parse available times for professional {professional_id} on {date}: {e}")
            return []

    async def book_appointment_on_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Realiza o agendamento (POST) na API."""
        try:
            endpoint = "/agendamentos"
            logger.info(f"Booking appointment with payload: {payload}")
            url = f"{self.base_url}{endpoint}"
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=payload, timeout=10.0)
                response.raise_for_status()
                booked_data = response.json()
                logger.info(f"Successfully booked appointment. Response: {booked_data}")
                return booked_data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while booking: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to book appointment: {e}")
            raise

if __name__ == "__main__":
    import asyncio

    async def main():
        client = AppHealthAPIClient()

        print("Buscando especialidades...")
        specialties = await client.get_specialties_from_api()
        if specialties:
            for spec in specialties:
                print(f"- ID: {spec.id}, Especialidade: {spec.especialidade}")
        else:
            print("Nenhuma especialidade encontrada ou erro na busca.")

        print("\nBuscando profissionais...")
        professionals = await client.get_professionals_from_api()
        if professionals:
            for prof in professionals:
                print(f"- ID: {prof.id}, Nome: {prof.nome}")
                for spec_link in prof.especialidades:
                    print(f"  - Especialidade Profissional: {spec_link.especialidade} (ID: {spec_link.id})")
        else:
            print("Nenhum profissional encontrado ou erro na busca.")

    asyncio.run(main())