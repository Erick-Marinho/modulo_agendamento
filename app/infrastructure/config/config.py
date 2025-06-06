from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
    """
    Configurações da aplicação
    """
    # === OpenAI Configuration ===
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY", description="Chave de API do OpenAI")
    OPENAI_MODEL_NAME: str = Field(..., env="OPENAI_MODEL_NAME", description="Modelo do OpenAI")
    OPENAI_TEMPERATURE: float = Field(..., env="OPENAI_TEMPERATURE", description="Temperatura para a geração de texto")

    # === MongoDB Configuration ===
    MONGODB_URI: str = Field(..., env="MONGODB_URI", description="URI do MongoDB")
    MONGODB_DB_NAME: str = Field(..., env="MONGODB_DB_NAME", description="Nome do banco de dados MongoDB")

    # === AppHealth API Configuration ===
    APPHEALTH_API_BASE_URL: str = Field(..., env="APPHEALTH_API_BASE_URL", description="Base URL da API do AppHealth")
    APPHEALTH_API_TOKEN: str = Field(..., env="APPHEALTH_API_TOKEN", description="Token da API do AppHealth")

     # === N8N Webhook Configuration ===
    N8N_WEBHOOK_URL: Optional[str] = Field(default=None, env="N8N_WEBHOOK_URL", description="URL do Webhook do N8N para enviar respostas")

    # === LangChain Configuration ===
    LANGCHAIN_TRACING_V2: Optional[bool] = Field(default=True, description="Habilitar tracing LangChain")
    LANGSMITH_API_KEY: Optional[str] = Field(default=None, description="Chave API LangSmith")
    LANGSMITH_PROJECT: Optional[str] = Field(default="modulo_agendamento", description="Projeto LangSmith")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

def mask_sensitive_data(value: str, show_chars: int = 4) -> str:
    """Mascara dados sensíveis mostrando apenas os últimos caracteres"""
    if not value or len(value) <= show_chars:
        return '*' * len(value) if value else 'Não definida'
    return '*' * (len(value) - show_chars) + value[-show_chars:]

settings = Settings()

if __name__ == "__main__":
    print("=== Configurações Carregadas ===")
    print(f"OpenAI API Key: {mask_sensitive_data(settings.OPENAI_API_KEY)}")
    print(f"OpenAI Model: {settings.OPENAI_MODEL_NAME}")
    print(f"OpenAI Temperature: {settings.OPENAI_TEMPERATURE}")
    print(f"MongoDB URI: {settings.MONGODB_URI}")
    print(f"MongoDB DB: {settings.MONGODB_DB_NAME}")
    print(f"AppHealth URL: {settings.APPHEALTH_API_BASE_URL}")
    print(f"AppHealth Token: {mask_sensitive_data(settings.APPHEALTH_API_TOKEN)}")
    