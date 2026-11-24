from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import (
    health_router, auth_router, edital_router,
    inscricao_router, documento_router, avaliacao_router,
    homologacao_router, auditoria_router, notificacao_router
)
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização: assegura diretório de armazenamento local (v5.0 §9)
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="QUERO - Quadro Universitário de Estágios Remunerados e Oportunidades - API RESTful (v5.0)",
    version="5.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Configuração de CORS para frontend SPA e deploys externos (Render, etc.)
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos roteadores da API v1
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(edital_router, prefix=settings.API_V1_PREFIX)
app.include_router(inscricao_router, prefix=settings.API_V1_PREFIX)
app.include_router(documento_router, prefix=settings.API_V1_PREFIX)
app.include_router(avaliacao_router, prefix=settings.API_V1_PREFIX)
app.include_router(homologacao_router, prefix=settings.API_V1_PREFIX)
app.include_router(auditoria_router, prefix=settings.API_V1_PREFIX)
app.include_router(notificacao_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {
        "sistema": settings.PROJECT_NAME,
        "sigla": "QUERO",
        "versao": "5.0.0",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health"
    }
