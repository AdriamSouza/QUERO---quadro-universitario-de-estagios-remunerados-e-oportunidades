import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import Usuario
from app.routers import (
    auditoria_router, auth_router, avaliacao_router, documento_router, edital_router, health_router,
    homologacao_router, inscricao_router, notificacao_router, usuarios_router,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("quero")


async def _definir_senhas_iniciais() -> None:
    """Atribui INITIAL_USERS_PASSWORD às contas existentes que ainda não possuem senha (ex.: carga inicial)."""
    if not settings.INITIAL_USERS_PASSWORD:
        return
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                update(Usuario)
                .where(Usuario.senha_hash.is_(None))
                .values(senha_hash=get_password_hash(settings.INITIAL_USERS_PASSWORD))
            )
            await session.commit()
            if res.rowcount:
                logger.info("Senha inicial definida para %s conta(s) sem senha.", res.rowcount)
    except Exception:
        logger.exception("Não foi possível definir as senhas iniciais.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.STORAGE_BACKEND == "local":
        import os
        os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    await _definir_senhas_iniciais()
    logger.info("QUERO iniciado (ambiente=%s, armazenamento=%s)", settings.ENVIRONMENT, settings.STORAGE_BACKEND)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="QUERO - Quadro Universitário de Estágios Remunerados e Oportunidades - API REST",
    version="5.1.0",
    docs_url="/docs" if settings.API_DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.API_DOCS_ENABLED else None,
    openapi_url="/api/v1/openapi.json" if settings.API_DOCS_ENABLED else None,
    lifespan=lifespan,
)

# O token é enviado no cabeçalho Authorization (sem cookies), portanto allow_credentials=False.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Conflitos de unicidade (ex.: duas submissões simultâneas) viram 409 em vez de erro interno."""
    logger.warning("IntegrityError em %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A operação conflita com um registro existente. Atualize a página e tente novamente."},
    )


for router in (
    health_router, auth_router, usuarios_router, edital_router, inscricao_router, documento_router,
    avaliacao_router, homologacao_router, auditoria_router, notificacao_router,
):
    app.include_router(router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {"sistema": settings.PROJECT_NAME, "sigla": "QUERO", "health": f"{settings.API_V1_PREFIX}/health"}
