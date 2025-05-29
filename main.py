import logging
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agendamento API",
    description="API para agendamento de serviços",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/", summary="Verifica se o servidor está online")
async def root():
    return {
        "status": "API FastAPI está online",
        "version": app.version,
        "docs": "/docs"
    }

