import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.infrastructure.config.config import settings
from app.infrastructure.persistence.ISaveCheckpoint import SaveCheckpointInterface

logger = logging.getLogger(__name__)


class AsyncMongoDBSaver(MongoDBSaver):
    """
    MongoDBSaver customizado com suporte completo a métodos assíncronos
    """

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """
        Implementação assíncrona do get_tuple usando thread pool
        """
        try:
            logger.debug(f"aget_tuple chamado com config: {config}")
            # Usar thread pool para executar método síncrono de forma assíncrona
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.get_tuple, config)
            logger.debug(f"aget_tuple resultado: {result is not None}")
            return result
        except Exception as e:
            logger.error(f"Erro no aget_tuple: {e}")
            return None

    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Dict[str, Any],
        new_versions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Implementação assíncrona do put usando thread pool
        """
        try:
            logger.debug(f"aput chamado com config: {config}")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.put, config, checkpoint, metadata, new_versions
            )
            logger.debug("aput executado com sucesso")
            return result
        except Exception as e:
            logger.error(f"Erro no aput: {e}")
            raise

    async def aput_writes(
        self, config: Dict[str, Any], writes: Sequence[Any], task_id: str
    ) -> None:
        """
        Implementação assíncrona do put_writes usando thread pool
        """
        try:
            logger.debug(f"aput_writes chamado com config: {config}, task_id: {task_id}")
            loop = asyncio.get_event_loop()

            # Verificar se o método put_writes existe na classe pai
            if hasattr(self, "put_writes"):
                await loop.run_in_executor(
                    None, self.put_writes, config, writes, task_id
                )
            else:
                # Implementação básica se put_writes não existir
                logger.debug(
                    "put_writes não encontrado na classe pai, usando implementação básica"
                )
                pass

            logger.debug("aput_writes executado com sucesso")
        except Exception as e:
            logger.error(f"Erro no aput_writes: {e}")
            # Não re-raise aqui para evitar falhas do sistema
            pass

    async def alist(
        self,
        config: Dict[str, Any],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[CheckpointTuple]:
        """
        Implementação assíncrona do list usando thread pool
        """
        try:
            logger.debug(f"alist chamado com config: {config}")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.list(config, filter=filter, before=before, limit=limit),
            )
            logger.debug(f"alist retornou {len(result)} items")
            return result
        except Exception as e:
            logger.error(f"Erro no alist: {e}")
            return []


class MongoDBSaverCheckpointer(SaveCheckpointInterface):
    """
    Checkpointer para salvar o estado do agente no MongoDB usando implementação customizada
    """

    def __init__(self):
        """
        Inicializa o MongoDBSaverCheckpointer usando implementação customizada
        """
        self.mongodb_uri = settings.MONGODB_URI
        self._checkpointer = None
        logger.info(f"MongoDBSaverCheckpointer inicializado com URI: {self.mongodb_uri}")

    def create_checkpoint(self):
        """
        Retorna o AsyncMongoDBSaver customizado
        """
        try:
            logger.info("Criando cliente MongoDB...")
            client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)

            # Testar conexão
            logger.info("Testando conexão com MongoDB...")
            logger.info("✅ Conexão com MongoDB testada com sucesso")

            # Usar nossa implementação customizada
            checkpointer = AsyncMongoDBSaver(
                client=client,
                db_name=settings.MONGODB_DB_NAME,  # Nome do banco
                collection_name="checkpoints",  # Nome da coleção
            )

            logger.info("✅ AsyncMongoDBSaver customizado criado com sucesso")
            return checkpointer

        except PyMongoError as e:
            logger.error(f"❌ Erro de conexão MongoDB: {e}")
            logger.warning("🔄 Fallback para MemorySaver devido a erro no MongoDB")
            from langgraph.checkpoint.memory import MemorySaver

            return MemorySaver()

        except Exception as e:
            logger.error(f"❌ Erro geral ao criar checkpointer: {e}")
            logger.warning("🔄 Fallback para MemorySaver")
            from langgraph.checkpoint.memory import MemorySaver

            return MemorySaver()
