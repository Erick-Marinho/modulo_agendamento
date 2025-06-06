import logging
import traceback

from langchain_core.messages import HumanMessage
from app.application.dto.message_request_dto import MessageRequestPayload
from app.application.agents.state.message_agent_state import MessageAgentState
from app.infrastructure.clients.n8n_client import N8NClient # Importar o novo cliente

logger = logging.getLogger(__name__)

class MessageService:
    """
    Serviço para processar a mensagem recebida e enviar a resposta.
    """

    def __init__(self, agent):
        """
        Inicializa o serviço de mensagem
        """
        if agent is None:
            raise ValueError("O agente não pode ser None para o MessageService")
        
        self.message_agent = agent
        self.n8n_client = N8NClient() # Instanciar o cliente N8N
        logger.info("MessageService inicializado com o agente e o cliente N8N.")

    async def process_message(self, request_payload: MessageRequestPayload) -> dict:
        """
        Processa a mensagem recebida, executa o agente e envia a resposta para o N8N.

        Args:
            request_payload: MessageRequestPayload

        Returns:
            Um dicionário com o status do envio para o N8N.
        """
        try:
            logger.info(f"=== INICIANDO PROCESSAMENTO DA MENSAGEM ===")
            logger.info(f"Payload recebido: {request_payload}")

            thread_id = request_payload.phone_number
            config = {"configurable": {"thread_id": thread_id}}

            initial_state: MessageAgentState = {
                "message": request_payload.message,
                "phone_number": request_payload.phone_number,
                "message_id": request_payload.message_id,
                "messages": [HumanMessage(content=request_payload.message)],
                "next_step": "",
                "conversation_context": None,
                "extracted_scheduling_details": None,
                "missing_fields": None,
                "awaiting_user_input": None
            }
            
            logger.info("=== EXECUTANDO AGENTE ===")
            final_state = await self.message_agent.ainvoke(initial_state, config=config)
            logger.info("=== AGENTE EXECUTADO COM SUCESSO ===")

            messages = final_state.get("messages", [])
            if not messages:
                logger.error(f"Estado final sem mensagens para a thread_id {thread_id}")
                # Mesmo em caso de erro, tentamos notificar
                return await self.n8n_client.send_text_message(
                    to_phone=request_payload.phone_number,
                    message_text="Desculpe, houve um problema interno. Tente novamente.",
                    original_received_message_id=request_payload.message_id
                )

            last_message = messages[-1]
            response_content = getattr(last_message, 'content', None)
            
            if not response_content:
                response_content = "Desculpe, não consegui gerar uma resposta. Como posso ajudar?"

            logger.info(f"=== ENVIANDO RESPOSTA PARA O N8N ===")
            # AQUI ESTÁ A MUDANÇA PRINCIPAL
            n8n_response = await self.n8n_client.send_text_message(
                to_phone=request_payload.phone_number,
                message_text=response_content,
                original_received_message_id=request_payload.message_id
            )

            return n8n_response

        except Exception as e:
            logger.error(f"=== ERRO CRÍTICO NO PROCESSAMENTO DA MENSAGEM ===")
            logger.error(f"Erro: {str(e)}")
            logger.error(traceback.format_exc())
            # Tenta notificar sobre o erro, se possível
            error_message = "Ocorreu um erro grave ao processar sua solicitação. A equipe técnica foi notificada."
            await self.n8n_client.send_text_message(
                to_phone=request_payload.phone_number,
                message_text=error_message,
                original_received_message_id=request_payload.message_id
            )
            # Re-lança a exceção para que o FastAPI retorne um 500
            raise