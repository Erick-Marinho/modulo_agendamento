from langchain_openai import ChatOpenAI
from app.application.agents.prompts.classify_message_prompt import CLASSIFY_MESSAGE_TEMPLATE
from app.application.interfaces.illm_service import ILLMService

from app.infrastructure.config.config import settings

class OpenAIService(ILLMService):
    def __init__(self) -> None:
        self.client = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL_NAME,
            temperature=settings.OPENAI_TEMPERATURE    
        )

    def classify_message(self, user_message: str) -> str:
        chain = CLASSIFY_MESSAGE_TEMPLATE | self.client
        llm_response = chain.invoke({"user_query": user_message})
        return llm_response.content