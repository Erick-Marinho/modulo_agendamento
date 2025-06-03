import logging
from langgraph.checkpoint.mongodb import MongoDBSaver
from app.infrastructure.persistence.ISaveCheckpoint import SaveCheckpointInterface
from app.infrastructure.config.config import settings
from pymongo import MongoClient


logger = logging.getLogger(__name__)

class MongoDBSaverCheckpointer(SaveCheckpointInterface):
    """
    Checkpointer para salvar o estado do agente no MongoDB usando o MongoDBSaver oficial do LangGraph
    """
    def __init__(self):
        """
        Inicializa o MongoDBSaverCheckpointer usando o MongoDBSaver oficial
        """
        self.mongodb_uri = settings.MONGODB_URI
        self._checkpointer = None
        logger.info(f"MongoDBSaverCheckpointer inicializado com URI: {self.mongodb_uri}")

    async def create_checkpoint(self):
        """
        Retorna o MongoDBSaver do LangGraph
        """
        try:            
            client = MongoClient(self.mongodb_uri)
            
            checkpointer = await MongoDBSaver(client)
            
            logger.info("MongoDBSaver criado com sucesso")
            return checkpointer
            
        except Exception as e:
            logger.error(f"Erro ao criar MongoDBSaver: {e}")
