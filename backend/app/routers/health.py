import os
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def check_health(db: AsyncSession = Depends(get_db)):
    """
    Verificação de integridade operacional do backend, conexão com PostgreSQL
    e disponibilidade do volume de armazenamento local.
    """
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    storage_status = "healthy"
    try:
        if not os.path.exists(settings.STORAGE_PATH):
            os.makedirs(settings.STORAGE_PATH, exist_ok=True)
        # Teste de escrita temporária
        test_file = os.path.join(settings.STORAGE_PATH, ".healthcheck")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
    except Exception as e:
        storage_status = f"unhealthy: {str(e)}"

    overall_status = "healthy" if db_status == "healthy" and storage_status == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        storage=storage_status,
        details={
            "environment": settings.ENVIRONMENT,
            "project": settings.PROJECT_NAME
        }
    )
