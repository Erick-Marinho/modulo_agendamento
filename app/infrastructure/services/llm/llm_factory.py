from enum import Enum

from app.application.interfaces.illm_service import ILLMService
from app.infrastructure.services.llm.openai_service import OpenAIService


class LLMFactory:
    @staticmethod
    def create_llm_service(provider: str) -> ILLMService:
        
        if provider == "openai":
            return OpenAIService()
        else:
            raise ValueError(f"Provedor LLM não suportado: {provider}")
