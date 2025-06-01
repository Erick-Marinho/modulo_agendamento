from abc import ABC, abstractmethod

class SaveCheckpointInterface(ABC):
    """
    Interface para salvar o estado do agente em memória
    """
    @abstractmethod
    def create_checkpoint(self):
        """
        Salva o estado do agente em memória
        """
        pass