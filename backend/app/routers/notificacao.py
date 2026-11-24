from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notificacao import Notificacao
from app.schemas.notificacao import NotificacaoResponse, NotificacaoListResponse

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("", response_model=NotificacaoListResponse)
async def listar_notificacoes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista notificações internas do usuário autenticado (v5.0 §11, TRV-01).
    """
    user_id = current_user["id"]
    query = (
        select(Notificacao)
        .where(Notificacao.usuario_id == user_id)
        .order_by(Notificacao.id.desc())
        .offset(skip)
        .limit(limit)
    )
    count_query = select(func.count(Notificacao.id)).where(Notificacao.usuario_id == user_id)

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    res = await db.execute(query)
    items = list(res.scalars().all())

    return NotificacaoListResponse(items=items, total=total)


@router.put("/{id}/lida", response_model=NotificacaoResponse)
async def marcar_notificacao_como_lida(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Marca notificação como lida."""
    query = select(Notificacao).where(
        and_(Notificacao.id == id, Notificacao.usuario_id == current_user["id"])
    )
    res = await db.execute(query)
    notif = res.scalar_one_or_none()
    if notif:
        notif.lida = True
        await db.commit()
        await db.refresh(notif)
    return notif
