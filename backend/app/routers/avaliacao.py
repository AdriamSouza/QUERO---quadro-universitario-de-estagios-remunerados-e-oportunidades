from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_client_ip, require_roles
from app.schemas.recurso import RecursoJulgamento, RecursoResponse
from app.services.avaliacao_service import AvaliacaoService
from app.services.workflow_service import get_db_sincronizado

router = APIRouter(tags=["Avaliações e Recursos"])


@router.post("/recursos/{id}/julgar", response_model=RecursoResponse)
async def julgar_recurso(
    id: int, data: RecursoJulgamento, request: Request,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """Julga recurso (AVA-04, RN-11). Em comissões com 2+ membros, o autor do parecer original não pode julgar."""
    return await AvaliacaoService.julgar_recurso(db, id, current_user, data, get_client_ip(request))
