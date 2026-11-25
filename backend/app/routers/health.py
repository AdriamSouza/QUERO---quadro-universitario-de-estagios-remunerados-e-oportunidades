import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import get_storage_service
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def check_health(response: Response, db: AsyncSession = Depends(get_db)):
    """Verificação de saúde do backend, do banco de dados e do armazenamento."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Healthcheck: falha no banco de dados")
        db_status = "unhealthy"

    storage_status = "healthy" if await get_storage_service().healthcheck() else "unhealthy"
    overall = "healthy" if db_status == "healthy" and storage_status == "healthy" else "degraded"
    if overall != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall,
        database=db_status,
        storage=storage_status,
        details={"environment": settings.ENVIRONMENT, "storage_backend": settings.STORAGE_BACKEND},
    )
