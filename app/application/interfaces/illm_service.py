from abc import ABC, abstractmethod


class ILLMService(ABC):
    """Interface base para serviço de LLM"""

    @abstractmethod
    def classify_message(self, message: str) -> str:
        pass