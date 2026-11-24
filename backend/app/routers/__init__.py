from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.edital import router as edital_router
from app.routers.inscricao import router as inscricao_router
from app.routers.documento import router as documento_router
from app.routers.avaliacao import router as avaliacao_router
from app.routers.homologacao import router as homologacao_router
from app.routers.auditoria import router as auditoria_router
from app.routers.notificacao import router as notificacao_router

__all__ = [
    "health_router",
    "auth_router",
    "edital_router",
    "inscricao_router",
    "documento_router",
    "avaliacao_router",
    "homologacao_router",
    "auditoria_router",
    "notificacao_router",
]
