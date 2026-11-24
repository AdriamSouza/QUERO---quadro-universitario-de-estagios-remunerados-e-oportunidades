import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import get_storage_service
from app.models.inscricao import Arquivo, Inscricao
from app.models.edital import ComissaoEdital

router = APIRouter(tags=["Arquivos"])


@router.get("/arquivos/{id}/download")
@router.get("/documentos/{id}/download")
async def download_arquivo(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download protegido de arquivo em streaming (v5.0 §11, RN-15, RNF-07).
    Acesso liberado apenas para:
    1. O próprio estudante titular.
    2. Avaliador formalmente designado na comissão do edital.
    3. Pró-Reitor.
    """
    stmt = (
        select(Arquivo)
        .options(joinedload(Arquivo.inscricao))
        .where(Arquivo.id == id)
    )
    res = await db.execute(stmt)
    arq = res.scalar_one_or_none()
    if not arq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")

    user_id = current_user["id"]
    user_roles = current_user.get("perfis", [current_user.get("perfil")])

    autorizado = False
    if "PRO_REITOR" in user_roles:
        autorizado = True
    elif arq.inscricao and arq.inscricao.estudante_id == user_id:
        autorizado = True
    elif "AVALIADOR" in user_roles and arq.inscricao:
        # Checa designação na comissão do edital
        comissao_stmt = select(ComissaoEdital).where(
            and_(
                ComissaoEdital.edital_id == arq.inscricao.edital_id,
                ComissaoEdital.avaliador_id == user_id
            )
        )
        comissao_res = await db.execute(comissao_stmt)
        if comissao_res.scalar_one_or_none():
            autorizado = True
    elif not arq.inscricao:
        # Arquivo de ata pública de homologação
        autorizado = True

    if not autorizado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado aos documentos deste candidato (RN-15, LGPD)."
        )

    storage = get_storage_service()
    try:
        stream = storage.get_file_stream(arq.chave)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo físico não localizado no volume de armazenamento."
        )

    return StreamingResponse(
        stream,
        media_type=arq.content_type or "application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{arq.nome_original}"',
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
        }
    )
