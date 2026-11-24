from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import MockAuthProvider
from app.models.user import Usuario
from sqlalchemy import select, text
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

    # Auto-provisionamento de usuários mock/contingência se USE_MOCK_AUTH=True
    if settings.USE_MOCK_AUTH:
        try:
            async with AsyncSessionLocal() as session:
                for mock_u in MockAuthProvider.MOCK_USERS.values():
                    stmt = select(Usuario).where(Usuario.id == mock_u["id"])
                    res = await session.execute(stmt)
                    existing = res.scalar_one_or_none()
                    if not existing:
                        user_obj = Usuario(
                            id=mock_u["id"],
                            cpf=mock_u["cpf"],
                            matricula=mock_u["matricula"],
                            nome=mock_u["nome"],
                            email=mock_u["email"],
                            perfil=mock_u["perfil"],
                            ativo=True,
                        )
                        session.add(user_obj)
                await session.commit()
                try:
                    await session.execute(text("SELECT setval(pg_get_serial_sequence('usuarios', 'id'), COALESCE((SELECT MAX(id) FROM usuarios), 1));"))
                    await session.commit()
                except Exception:
                    pass
        except Exception as e:
            print(f"[Lifespan] Mock users sync: {e}")

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
