from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import require_roles
from app.schemas.recurso import RecursoJulgamento, RecursoResponse
from app.services.avaliacao_service import AvaliacaoService

router = APIRouter(tags=["Avaliações e Recursos"])


@router.post("/recursos/{id}/julgar", response_model=RecursoResponse)
async def julgar_recurso(
    id: int,
    data: RecursoJulgamento,
    request: Request,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Julga recurso de seleção preliminar (v5.0 §11, AVA-04, RN-11).
    Bloqueia (HTTP 403) o autor do parecer original em bancas com 2 ou mais membros.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await AvaliacaoService.julgar_recurso(
        db=db,
        recurso_id=id,
        julgador_id=current_user["id"],
        data=data,
        ip_origem=client_ip
    )
