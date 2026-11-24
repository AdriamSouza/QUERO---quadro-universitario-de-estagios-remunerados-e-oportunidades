from fastapi import APIRouter, Depends, Request, Response, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict
import io

from app.core.database import get_db
from app.core.security import require_roles, get_current_user
from app.schemas.inscricao import (
    InscricaoResponse, InscricaoListResponse,
    InscricaoReanalisarRequest, InscricaoDesistirRequest
)
from app.schemas.avaliacao import AvaliacaoInput, AvaliacaoResponse
from app.schemas.recurso import RecursoCreate, RecursoResponse
from app.services.inscricao_service import InscricaoService
from app.services.avaliacao_service import AvaliacaoService

router = APIRouter(prefix="/inscricoes", tags=["Inscrições"])


@router.get("/me", response_model=List[InscricaoResponse])
async def listar_minhas_inscricoes(
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista inscrições, status e resultados do estudante logado (v5.0 §11, INS-06).
    """
    return await InscricaoService.listar_minhas_inscricoes(
        db=db,
        estudante_id=current_user["id"]
    )


@router.get("/{id}", response_model=InscricaoResponse)
async def get_inscricao(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retorna detalhes da inscrição com verificação de autorização."""
    inscricao = await InscricaoService.get_inscricao_by_id(db, id)
    # Permite acesso ao titular, avaliador ou pró-reitor (RN-15)
    user_roles = current_user.get("perfis", [current_user.get("perfil")])
    if "PRO_REITOR" not in user_roles and "AVALIADOR" not in user_roles and inscricao.estudante_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao titular ou comissão avaliadora (RN-15).")
    return inscricao


@router.put("/{id}/retificar", response_model=InscricaoResponse)
async def retificar_inscricao(
    id: int,
    request: Request,
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Substitui PDFs no prazo regulamentar mantendo protocolo e CR congelado (v5.0 §11, INS-05, RN-02).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    form = await request.form()
    arquivos_dict: Dict[int, UploadFile] = {}

    for key, value in form.items():
        if isinstance(value, UploadFile):
            num_part = "".join(filter(str.isdigit, key))
            if num_part:
                arquivos_dict[int(num_part)] = value

    if not arquivos_dict:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhum arquivo enviado para retificação. Indique os arquivos nos campos 'doc_{id}'."
        )

    return await InscricaoService.retificar_inscricao(
        db=db,
        inscricao_id=id,
        estudante_id=current_user["id"],
        arquivos_retificados=arquivos_dict,
        ip_origem=client_ip
    )


@router.post("/{id}/desistir", response_model=InscricaoResponse)
async def desistir_inscricao(
    id: int,
    data: InscricaoDesistirRequest,
    request: Request,
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Marca inscrição como Desistente antes da publicação do resultado preliminar (v5.0 §11, INS-07).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await InscricaoService.desistir_inscricao(
        db=db,
        inscricao_id=id,
        estudante_id=current_user["id"],
        data=data,
        ip_origem=client_ip
    )


@router.get("/{id}/comprovante")
async def baixar_comprovante_inscricao(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Emite e baixa comprovante digital de inscrição com protocolo único em formato PDF (v5.0 §11, INS-04).
    """
    inscricao = await InscricaoService.get_inscricao_by_id(db, id)
    user_roles = current_user.get("perfis", [current_user.get("perfil")])
    if "PRO_REITOR" not in user_roles and inscricao.estudante_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao titular da inscrição.")

    data_subm = inscricao.data_submissao_original.strftime("%d/%m/%Y às %H:%M:%S")
    corpo = f"""
================================================================================
     QUERO - QUADRO UNIVERSITÁRIO DE ESTÁGIOS REMUNERADOS E OPORTUNIDADES
================================================================================
                    COMPROVANTE OFICIAL DE INSCRIÇÃO
--------------------------------------------------------------------------------
Protocolo Único: {inscricao.protocolo}
Edital: {inscricao.edital.titulo} (ID: {inscricao.edital_id})
Candidato: {inscricao.estudante.nome}
Matrícula: {inscricao.estudante.matricula or "N/A"}
Curso Congelado: {inscricao.curso_congelado}
CR Congelado: {float(inscricao.cr_congelado or 0.0):.2f}
Data/Hora Oficial: {data_subm} (Horário de Brasília)
Situação Formal: {inscricao.status}
--------------------------------------------------------------------------------
Documento emitido eletronicamente pela plataforma QUERO.
Autenticidade garantida pelo identificador de protocolo unificado.
================================================================================
"""
    stream_content = f"BT /F1 10 Tf 36 760 Td 14 TL\n"
    for linha in corpo.encode("latin-1", errors="replace").decode("latin-1").split("\n"):
        stream_content += f"({linha}) '\n"
    stream_content += "ET"
    stream_bytes = stream_content.encode("latin-1", errors="replace")

    header_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    stream_obj = (
        f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        f"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
        f"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n"
        f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n"
    ).encode("ascii") + stream_bytes + b"\nendstream\nendobj\n"

    trailer_bytes = (
        f"xref\n0 6\n0000000000 65535 f \n"
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{len(header_bytes) + len(stream_obj)}\n%%EOF"
    ).encode("ascii")

    pdf_output = header_bytes + stream_obj + trailer_bytes

    return Response(
        content=pdf_output,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="comprovante_{inscricao.protocolo}.pdf"'}
    )


@router.post("/{id}/reanalisar", response_model=InscricaoResponse)
async def reanalisar_inscricao(
    id: int,
    data: InscricaoReanalisarRequest,
    request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Reanálise manual de indeferimento até o início da avaliação (v5.0 §11, RN-05, RN-14).
    Apenas PRO_REITOR.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await InscricaoService.reanalisar_inscricao(
        db=db,
        inscricao_id=id,
        data=data,
        user_id=current_user["id"],
        ip_origem=client_ip
    )


@router.put("/{id}/avaliacao", response_model=AvaliacaoResponse)
async def avaliar_candidatura(
    id: int,
    data: AvaliacaoInput,
    request: Request,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Salva rascunho ou confirma avaliação com nota, parecer e declaração (v5.0 §11, AVA-01, RN-07, RN-08).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await AvaliacaoService.avaliar_inscricao(
        db=db,
        inscricao_id=id,
        avaliador_id=current_user["id"],
        data=data,
        ip_origem=client_ip
    )


@router.post("/{id}/recursos", response_model=RecursoResponse, status_code=status.HTTP_201_CREATED)
async def interpor_recurso(
    id: int,
    data: RecursoCreate,
    request: Request,
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Interpõe recurso único na janela do edital (v5.0 §11, AVA-03, RN-10).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await AvaliacaoService.interpor_recurso(
        db=db,
        inscricao_id=id,
        estudante_id=current_user["id"],
        data=data,
        ip_origem=client_ip
    )
