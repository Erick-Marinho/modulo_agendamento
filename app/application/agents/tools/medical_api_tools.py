import logging
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel
from datetime import datetime

from app.infrastructure.interfaces.imedical_repository import IMedicalRepository
from app.domain.value_objects.tool_result import ToolResult, ToolStatus
from app.domain.entities.medical_specialty import ApiMedicalSpecialty
from app.domain.entities.medical_professional import ApiMedicalProfessional
from app.infrastructure.clients.apphealth_api_client import AppHealthAPIClient


logger = logging.getLogger(__name__)


class NoArgsSchema(BaseModel):
    pass


class MedicalApiTools:
    def __init__(self, medical_repository: IMedicalRepository, api_client: AppHealthAPIClient):
        self.medical_repository = medical_repository
        self.api_client = api_client

        self.get_available_specialties = create_get_available_specialties_tool(
            medical_repository
        )
        self.get_professionals_by_specialty = (
            create_get_professionals_by_specialty_tool(medical_repository)
        )
        self.check_availability = create_check_availability_tool(
            medical_repository, self.api_client
        )


def create_get_available_specialties_tool(medical_repository: IMedicalRepository):
    @tool(args_schema=NoArgsSchema)
    async def get_available_specialties() -> str:
        """
        Busca e retorna uma lista formatada de todas as especialidades médicas disponíveis na clínica.
        Esta tool é útil quando o usuário pergunta sobre quais especialidades a clínica oferece.
        """
        logger.info("Tool 'get_available_specialties' foi chamada.")
        try:
            specialties: List[ApiMedicalSpecialty] = (
                await medical_repository.get_all_api_specialties()
            )

            if not specialties:
                result = ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    message="No momento, não encontrei nenhuma especialidade médica disponível em nossos registros. Por favor, verifique mais tarde ou entre em contato.",
                )
                return result.message

            specialties_list_str = "\n".join(
                [f"- {spec.especialidade}" for spec in specialties]
            )

            response_message = (
                f"Encontrei as seguintes especialidades médicas disponíveis na clínica:\n"
                f"{specialties_list_str}\n\n"
                f"Você gostaria de ver os profissionais de alguma dessas especialidades?"
            )

            result = ToolResult(
                status=ToolStatus.SUCCESS,
                message=response_message,
                data={
                    "specialties_count": len(specialties),
                    "specialties_names": [s.especialidade for s in specialties],
                },
            )
            logger.info(
                f"Tool 'get_available_specialties' retornou {len(specialties)} especialidades."
            )
            return result.message

        except Exception as e:
            logger.error(
                f"Erro na tool 'get_available_specialties': {str(e)}", exc_info=True
            )
            error_result = ToolResult(
                status=ToolStatus.ERROR,
                message="Desculpe, ocorreu um erro interno ao tentar buscar as especialidades disponíveis. Tente novamente mais tarde.",
            )
            return error_result.message

    return get_available_specialties


def create_get_professionals_by_specialty_tool(medical_repository: IMedicalRepository):
    @tool
    async def get_professionals_by_specialty(specialty_name: str) -> str:
        """
        Busca e retorna uma lista formatada de profissionais médicos para uma especialidade específica.
        Use esta tool quando o usuário perguntar por médicos de uma determinada especialidade, por exemplo, 'Quais cardiologistas vocês têm?'.
        Args:
            specialty_name (str): O nome da especialidade médica a ser pesquisada. Por exemplo, 'Cardiologia'.
        """
        logger.info(
            f"Tool 'get_professionals_by_specialty' foi chamada com specialty_name: '{specialty_name}'"
        )
        if not specialty_name or not specialty_name.strip():
            return ToolResult(
                status=ToolStatus.VALIDATION_ERROR,
                message="Por favor, informe um nome de especialidade válido para a busca.",
            ).message

        try:
            professionals: List[ApiMedicalProfessional] = (
                await medical_repository.get_professionals_by_specialty_name(
                    specialty_name
                )
            )

            if not professionals:
                result = ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    message=f"Não encontrei profissionais para a especialidade '{specialty_name}'. Verifique se o nome da especialidade está correto ou você pode perguntar pelas especialidades disponíveis.",
                )
                return result.message

            professionals_list_str = "\n".join(
                [f"- {prof.nome}" for prof in professionals]
            )

            response_message = (
                f"Para a especialidade '{specialty_name}', encontrei os seguintes profissionais:\n"
                f"{professionals_list_str}\n\n"
                f"Gostaria de agendar com algum deles ou saber mais detalhes?"
            )

            result = ToolResult(
                status=ToolStatus.SUCCESS,
                message=response_message,
                data={
                    "specialty_searched": specialty_name,
                    "professionals_count": len(professionals),
                },
            )
            logger.info(
                f"Tool 'get_professionals_by_specialty' para '{specialty_name}' retornou {len(professionals)} profissionais."
            )
            return result.message

        except Exception as e:
            logger.error(
                f"Erro na tool 'get_professionals_by_specialty' para '{specialty_name}': {str(e)}",
                exc_info=True,
            )
            error_result = ToolResult(
                status=ToolStatus.ERROR,
                message=f"Desculpe, ocorreu um erro interno ao tentar buscar os profissionais para '{specialty_name}'. Tente novamente mais tarde.",
            )
            return error_result.message

    return get_professionals_by_specialty

async def _get_professional_id_by_name(
    professional_name: str, repository: IMedicalRepository
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

# Nova Tool para checar disponibilidade
def create_check_availability_tool(medical_repository: IMedicalRepository, api_client: AppHealthAPIClient):
    @tool
    async def check_availability(professional_name: str, month: Optional[int] = None, year: Optional[int] = None) -> str:
        """
        Verifica as datas e horários disponíveis para um profissional específico.
        Use esta tool quando o usuário perguntar sobre a agenda, datas ou horários disponíveis para um médico.
        É OBRIGATÓRIO ter o nome do profissional para usar esta tool.
        Args:
            professional_name (str): O nome do profissional de saúde.
            month (int, optional): O mês para verificar a disponibilidade (e.g., 6 para Junho). Padrão para o mês atual.
            year (int, optional): O ano para verificar a disponibilidade (e.g., 2025). Padrão para o ano atual.
        """
        logger.info(f"Tool 'check_availability' foi chamada para o profissional: '{professional_name}'")
        if not professional_name:
            return ToolResult(
                status=ToolStatus.VALIDATION_ERROR,
                message="O nome do profissional é obrigatório para verificar a disponibilidade."
            ).message

        try:
            professional_id = await _get_professional_id_by_name(professional_name, medical_repository)
            if not professional_id:
                return ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    message=f"Não consegui encontrar um profissional com o nome '{professional_name}'. Poderia verificar o nome e tentar novamente?"
                ).message

            now = datetime.now()
            check_month = month or now.month
            check_year = year or now.year

            available_dates_raw = await api_client.get_available_dates_from_api(professional_id, check_month, check_year)
            if not available_dates_raw:
                return ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    message=f"Não encontrei datas disponíveis para {professional_name} em {check_month}/{check_year}. Gostaria de tentar outro mês?"
                ).message

            # Limitar a quantidade de datas para não poluir a resposta
            dates_to_show = [d['data'] for d in available_dates_raw[:5]] # Mostra as próximas 5 datas
            formatted_dates = [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y") for d in dates_to_show]

            response_message = f"Encontrei as seguintes datas disponíveis para {professional_name}:\n- " + "\n- ".join(formatted_dates)
            response_message += f"\n\nSe alguma dessas datas for boa para você, me diga qual e posso verificar os horários."

            return ToolResult(
                status=ToolStatus.SUCCESS,
                message=response_message
            ).message

        except Exception as e:
            logger.error(f"Erro na tool 'check_availability': {str(e)}", exc_info=True)
            return ToolResult(
                status=ToolStatus.ERROR,
                message=f"Desculpe, ocorreu um erro interno ao buscar a agenda de {professional_name}. Tente novamente mais tarde."
            ).message
            
    return check_availability
