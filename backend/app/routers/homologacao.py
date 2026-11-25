from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import require_roles
from app.models.homologacao import AtaHomologacao
from app.routers._download import stream_arquivo

router = APIRouter(tags=["Atas e Exportações"])


async def _ultima_ata(db: AsyncSession, edital_id: int, relacao) -> AtaHomologacao:
    ata = (await db.execute(
        select(AtaHomologacao)
        .where(AtaHomologacao.edital_id == edital_id)
        .options(joinedload(relacao))
        .order_by(AtaHomologacao.id.desc())
        .limit(1)
    )).scalars().first()
    if not ata:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="O resultado final deste edital ainda não foi homologado.")
    return ata


@router.get("/editais/{id}/ata-pdf")
async def download_ata_oficial_pdf(id: int, db: AsyncSession = Depends(get_db)):
    """Ata de homologação em PDF (documento público - HOM-02)."""
    ata = await _ultima_ata(db, id, AtaHomologacao.arquivo_pdf)
    return await stream_arquivo(ata.arquivo_pdf.chave, f"ata_homologacao_edital_{id}.pdf", "application/pdf")


@router.get("/editais/{id}/folha-csv")
async def download_folha_csv(
    id: int,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Lista final em CSV com dados pessoais (restrita à Pró-Reitoria - HOM-02)."""
    ata = await _ultima_ata(db, id, AtaHomologacao.arquivo_csv)
    return await stream_arquivo(ata.arquivo_csv.chave, f"lista_aprovados_edital_{id}.csv", "text/csv; charset=utf-8")
