from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notificacao import Notificacao
from app.schemas.notificacao import NotificacaoListResponse, NotificacaoResponse

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("", response_model=NotificacaoListResponse)
async def listar_notificacoes(
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filtro = Notificacao.usuario_id == current_user["id"]
    total = (await db.execute(select(func.count(Notificacao.id)).where(filtro))).scalar() or 0
    nao_lidas = (await db.execute(
        select(func.count(Notificacao.id)).where(filtro, Notificacao.lida.is_(False))
    )).scalar() or 0
    items = (await db.execute(
        select(Notificacao).where(filtro).order_by(Notificacao.id.desc()).offset(skip).limit(limit)
    )).scalars().all()
    return NotificacaoListResponse(items=list(items), total=total, nao_lidas=nao_lidas)


@router.put("/lidas")
async def marcar_todas_como_lidas(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notificacao)
        .where(Notificacao.usuario_id == current_user["id"], Notificacao.lida.is_(False))
        .values(lida=True)
    )
    await db.commit()
    return {"status": "sucesso"}


@router.put("/{id}/lida", response_model=NotificacaoResponse)
async def marcar_notificacao_como_lida(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notif = (await db.execute(
        select(Notificacao).where(and_(Notificacao.id == id, Notificacao.usuario_id == current_user["id"]))
    )).scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificação não encontrada.")
    notif.lida = True
    await db.commit()
    await db.refresh(notif)
    return notif
