from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List

from app.core.database import get_db
from app.core.security import require_roles
from app.models.auditoria import AuditoriaLog
from app.schemas.auditoria import AuditoriaLogResponse, AuditoriaLogListResponse

router = APIRouter(tags=["Auditoria"])


@router.get("/auditoria", response_model=AuditoriaLogListResponse)
@router.get("/auditoria/logs", response_model=AuditoriaLogListResponse)
async def list_audit_logs(
    entidade: Optional[str] = Query(None, description="Filtrar por entidade: editais, inscricoes, avaliacoes, recursos"),
    entidade_id: Optional[int] = Query(None, description="Filtrar por ID do registro da entidade"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Consulta a trilha de auditoria imutável (v5.0 §11, TRV-03, RN-14).
    Acesso restrito ao perfil PRO_REITOR.
    """
    query = select(AuditoriaLog)
    count_query = select(func.count(AuditoriaLog.id))

    filters = []
    if entidade:
        filters.append(AuditoriaLog.entidade == entidade)
    if entidade_id:
        filters.append(AuditoriaLog.entidade_id == entidade_id)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(AuditoriaLog.id.desc()).offset(skip).limit(limit)
    res = await db.execute(query)
    items = list(res.scalars().all())

    return AuditoriaLogListResponse(items=items, total=total)
