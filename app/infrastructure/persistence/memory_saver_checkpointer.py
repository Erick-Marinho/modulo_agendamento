import logging

from langgraph.checkpoint.memory import MemorySaver

from app.infrastructure.persistence.ISaveCheckpoint import SaveCheckpointInterface

logger = logging.getLogger(__name__)

class MemorySaverCheckpointer(SaveCheckpointInterface):
    """
    Checkpointer para salvar o estado do agente em memória
    """
    def __init__(self):
        """
        Inicializa o MemorySaverCheckpointer
        """
        self.memory_saver = MemorySaver()

    def create_checkpoint(self):
        """
        Retorna o MemorySaver
        """
        return self.memory_saver