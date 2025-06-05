import logging
import asyncio
from typing import List
from langchain_core.tools import tool 
from pydantic import BaseModel

from app.infrastructure.interfaces.imedical_repository import IMedicalRepository
from app.domain.value_objects.tool_result import ToolResult, ToolStatus
from app.domain.entities.medical_specialty import ApiMedicalSpecialty
from app.domain.entities.medical_professional import ApiMedicalProfessional

logger = logging.getLogger(__name__)

class NoArgsSchema(BaseModel):
    pass

class MedicalApiTools:
    def __init__(self, medical_repository: IMedicalRepository):
        self.medical_repository = medical_repository
        
        self.get_available_specialties = create_get_available_specialties_tool(medical_repository)
        self.get_professionals_by_specialty = create_get_professionals_by_specialty_tool(medical_repository)

def create_get_available_specialties_tool(medical_repository: IMedicalRepository):
    @tool(args_schema=NoArgsSchema) 
    async def get_available_specialties() -> str:
        """
        Busca e retorna uma lista formatada de todas as especialidades médicas disponíveis na clínica.
        Esta tool é útil quando o usuário pergunta sobre quais especialidades a clínica oferece.
        """
        logger.info("Tool 'get_available_specialties' foi chamada.")
        try:
            specialties: List[ApiMedicalSpecialty] = await medical_repository.get_all_api_specialties()
            
            if not specialties:
                result = ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    message="No momento, não encontrei nenhuma especialidade médica disponível em nossos registros. Por favor, verifique mais tarde ou entre em contato."
                )
                return result.message

            specialties_list_str = "\n".join([f"- {spec.especialidade}" for spec in specialties])
            
            response_message = (
                f"Encontrei as seguintes especialidades médicas disponíveis na clínica:\n"
                f"{specialties_list_str}\n\n"
                f"Você gostaria de ver os profissionais de alguma dessas especialidades?"
            )
            
            result = ToolResult(
                status=ToolStatus.SUCCESS,
                message=response_message,
                data={"specialties_count": len(specialties), "specialties_names": [s.especialidade for s in specialties]}
            )
            logger.info(f"Tool 'get_available_specialties' retornou {len(specialties)} especialidades.")
            return result.message
            
        except Exception as e:
            logger.error(f"Erro na tool 'get_available_specialties': {str(e)}", exc_info=True)
            error_result = ToolResult(
                status=ToolStatus.ERROR,
                message="Desculpe, ocorreu um erro interno ao tentar buscar as especialidades disponíveis. Tente novamente mais tarde."
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
        logger.info(f"Tool 'get_professionals_by_specialty' foi chamada com specialty_name: '{specialty_name}'")
        if not specialty_name or not specialty_name.strip():
            return ToolResult(status=ToolStatus.VALIDATION_ERROR, message="Por favor, informe um nome de especialidade válido para a busca.").message

        try:
            professionals: List[ApiMedicalProfessional] = await medical_repository.get_professionals_by_specialty_name(specialty_name)
            
            if not professionals:
                result = ToolResult(
                    status=ToolStatus.NOT_FOUND,
                    message=f"Não encontrei profissionais para a especialidade '{specialty_name}'. Verifique se o nome da especialidade está correto ou você pode perguntar pelas especialidades disponíveis."
                )
                return result.message

            professionals_list_str = "\n".join([f"- {prof.nome}" for prof in professionals])
            
            response_message = (
                f"Para a especialidade '{specialty_name}', encontrei os seguintes profissionais:\n"
                f"{professionals_list_str}\n\n"
                f"Gostaria de agendar com algum deles ou saber mais detalhes?"
            )
            
            result = ToolResult(
                status=ToolStatus.SUCCESS,
                message=response_message,
                data={"specialty_searched": specialty_name, "professionals_count": len(professionals)}
            )
            logger.info(f"Tool 'get_professionals_by_specialty' para '{specialty_name}' retornou {len(professionals)} profissionais.")
            return result.message

        except Exception as e:
            logger.error(f"Erro na tool 'get_professionals_by_specialty' para '{specialty_name}': {str(e)}", exc_info=True)
            error_result = ToolResult(
                status=ToolStatus.ERROR,
                message=f"Desculpe, ocorreu um erro interno ao tentar buscar os profissionais para '{specialty_name}'. Tente novamente mais tarde."
            )
            return error_result.message
    
    return get_professionals_by_specialty