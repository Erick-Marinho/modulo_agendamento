import logging
from langgraph.checkpoint.mongodb import MongoDBSaver
from app.infrastructure.persistence.ISaveCheckpoint import SaveCheckpointInterface
from app.infrastructure.config.config import settings
from pymongo import MongoClient # IMPORTAR MongoClient

logger = logging.getLogger(__name__)

class MongoDBSaverCheckpointer(SaveCheckpointInterface):
    """
    Checkpointer para salvar o estado do agente no MongoDB usando o MongoDBSaver oficial do LangGraph
    """
    def __init__(self):
        """
        Inicializa o MongoDBSaverCheckpointer.
        """
        self.mongodb_uri = settings.MONGODB_URI
        self.db_name = settings.MONGODB_DB_NAME
        self.collection_name = "langgraph_checkpoints" 
        self._client = None 
        logger.info(f"MongoDBSaverCheckpointer inicializado com URI: {self.mongodb_uri}, DB: {self.db_name}")

    async def _get_client(self):
        """Helper para obter ou criar a instância do cliente MongoDB."""
        if self._client is None:
            self._client = MongoClient(self.mongodb_uri)
            logger.info("Cliente MongoDB conectado.")
        return self._client

    async def create_checkpoint(self) -> MongoDBSaver:
        """
        Retorna uma instância do MongoDBSaver do LangGraph.
        """
        try:
            client = await self._get_client() 
            checkpointer = MongoDBSaver(
                client=client, 
                db_name=self.db_name,
                collection_name=self.collection_name 
            )
            
            logger.info(f"MongoDBSaver instanciado com sucesso para db: '{self.db_name}', collection: '{self.collection_name}'.")
            return checkpointer
            
        except Exception as e:
            logger.error(f"Erro ao criar MongoDBSaver: {e}", exc_info=True)
            raise

    
    async def close_connection(self):
        if self._client:
            self._client.close()
            logger.info("Conexão MongoDB fechada.")
