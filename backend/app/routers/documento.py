from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.homologacao import AtaHomologacao
from app.models.inscricao import Arquivo
from app.routers._download import stream_arquivo
from app.services.edital_service import EditalService

router = APIRouter(tags=["Arquivos"])


@router.get("/arquivos/{id}/download")
@router.get("/documentos/{id}/download")
async def download_arquivo(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download protegido de documento (RN-15, LGPD): titular, avaliador designado na comissão do edital
    e Pró-Reitoria. Para atas, o PDF é público e a lista CSV é restrita à Pró-Reitoria.
    """
    arq = (await db.execute(
        select(Arquivo).options(joinedload(Arquivo.inscricao)).where(Arquivo.id == id)
    )).scalar_one_or_none()
    if not arq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")

    perfis = current_user["perfis"]
    autorizado = "PRO_REITOR" in perfis
    if not autorizado and arq.inscricao:
        if arq.inscricao.estudante_id == current_user["id"]:
            autorizado = True
        elif "AVALIADOR" in perfis:
            autorizado = await EditalService.usuario_na_comissao(db, arq.inscricao.edital_id, current_user["id"])
    elif not autorizado:
        ata_pdf = (await db.execute(
            select(AtaHomologacao.id).where(AtaHomologacao.arquivo_pdf_id == arq.id)
        )).scalar_one_or_none()
        autorizado = ata_pdf is not None

    if not autorizado:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para acessar este documento.")

    return await stream_arquivo(arq.chave, arq.nome_original, arq.content_type or "application/pdf", inline=True)
