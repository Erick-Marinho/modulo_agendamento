import httpx
import logging
import json
from typing import Dict, Any, Optional
from app.infrastructure.config.config import settings

logger = logging.getLogger(__name__)

class N8NClient:
    """
    Cliente para enviar mensagens para um webhook do N8N.
    """
    def __init__(self):
        self.n8n_webhook_url = settings.N8N_WEBHOOK_URL
        self.n8n_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def send_text_message(self, to_phone: str, message_text: str, original_received_message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Envia uma mensagem de texto para o webhook configurado.
        """
        if not self.n8n_webhook_url:
            logger.error("N8N_WEBHOOK_URL não configurada. Não é possível enviar a mensagem de resposta.")
            return {"error": "ConfigurationError", "details": "N8N_WEBHOOK_URL não está configurada."}

        n8n_payload: Dict[str, Any] = {
            "phone": to_phone,
            "message": message_text,
            "original_received_message_id": original_received_message_id
        }
        
        payload_json = json.dumps(n8n_payload)
        
        logger.info(f"N8N_CLIENT: Enviando mensagem para webhook. Destinatário: {to_phone}. Texto: '{message_text[:50]}...'.")
        logger.debug(f"N8N_CLIENT: Payload: {payload_json}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.n8n_webhook_url,
                    content=payload_json,
                    headers=self.n8n_headers
                )
                response.raise_for_status()
                
                response_content = response.text
                logger.info(f"N8N_CLIENT: Mensagem enviada com sucesso. Status: {response.status_code}. Resposta: {response_content[:200]}")
                return {"status_code": response.status_code, "response_body": response_content}

            except httpx.HTTPStatusError as e:
                logger.error(f"N8N_CLIENT: Erro HTTP ao enviar para webhook. Status: {e.response.status_code}. Detalhes: {e.response.text}", exc_info=True)
                error_details = {"error": "HTTPStatusError", "status_code": e.response.status_code, "request_payload": n8n_payload}
                try:
                    error_details["response_body"] = e.response.json()
                except json.JSONDecodeError:
                    error_details["response_body"] = e.response.text
                return error_details
            
            except httpx.RequestError as e:
                logger.error(f"N8N_CLIENT: Erro de requisição ao enviar para webhook (URL: {e.request.url}): {str(e)}", exc_info=True)
                return {"error": "RequestError", "details": str(e), "request_payload": n8n_payload}

            except Exception as e:
                logger.error(f"N8N_CLIENT: Erro inesperado ao enviar para webhook: {str(e)}", exc_info=True)
                return {"error": "UnexpectedError", "details": str(e), "request_payload": n8n_payload}