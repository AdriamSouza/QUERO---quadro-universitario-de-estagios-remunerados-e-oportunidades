from fastapi import APIRouter, Depends, Request, Response, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import io

from app.core.database import get_db
from app.core.security import require_roles
from app.core.storage import get_storage_service
from app.models.homologacao import AtaHomologacao
from app.models.inscricao import Arquivo

router = APIRouter(tags=["Atas e Exportações"])


@router.get("/editais/{id}/ata-pdf")
async def download_ata_oficial_pdf(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Download público da Ata Oficial de Homologação em formato PDF padronizado (v5.0 HOM-02).
    """
    res = await db.execute(
        select(AtaHomologacao)
        .where(AtaHomologacao.edital_id == id)
        .options(joinedload(AtaHomologacao.arquivo_pdf))
        .order_by(AtaHomologacao.id.desc())
    )
    ata = res.scalar_one_or_none()
    if not ata or not ata.arquivo_pdf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ata de homologação não disponível para este edital.")

    storage = get_storage_service()
    stream = storage.get_file_stream(ata.arquivo_pdf.chave)

    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ata_homologacao_edital_{id}.pdf"',
        }
    )


@router.get("/editais/{id}/folha-csv")
async def download_folha_csv(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Download da lista oficial final de aprovados em formato CSV (v5.0 HOM-02).
    """
    res = await db.execute(
        select(AtaHomologacao)
        .where(AtaHomologacao.edital_id == id)
        .options(joinedload(AtaHomologacao.arquivo_csv))
        .order_by(AtaHomologacao.id.desc())
    )
    ata = res.scalar_one_or_none()
    if not ata or not ata.arquivo_csv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lista de aprovados em CSV não disponível para este edital.")

    storage = get_storage_service()
    stream = storage.get_file_stream(ata.arquivo_csv.chave)

    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="lista_aprovados_edital_{id}.csv"',
        }
    )
