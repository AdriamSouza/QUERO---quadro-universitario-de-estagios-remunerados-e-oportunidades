from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_client_ip, get_current_user, require_roles
from app.routers._upload import extrair_documentos, ler_formulario
from app.schemas.avaliacao import AvaliacaoInput, AvaliacaoResponse
from app.schemas.inscricao import InscricaoDesistirRequest, InscricaoReanalisarRequest, InscricaoResponse
from app.schemas.recurso import RecursoCreate, RecursoResponse
from app.services.avaliacao_service import FASES_RESULTADO_PUBLICO, AvaliacaoService
from app.services.edital_service import EditalService
from app.services.inscricao_service import InscricaoService
from app.services.report_service import ReportService
from app.services.workflow_service import STATUS_INSCRICAO_LABEL, get_db_sincronizado

router = APIRouter(prefix="/inscricoes", tags=["Inscrições"])


def _visao_estudante(inscricao) -> InscricaoResponse:
    """O estudante só vê a própria nota após a publicação do resultado preliminar."""
    resp = InscricaoResponse.model_validate(inscricao)
    if resp.status_edital not in FASES_RESULTADO_PUBLICO:
        resp.avaliacao_resumo = None
    return resp


async def _autorizar_leitura(db: AsyncSession, inscricao, user: dict) -> None:
    """Titular, Pró-Reitoria ou avaliador designado na comissão do edital (RN-15)."""
    if inscricao.estudante_id == user["id"] or "PRO_REITOR" in user["perfis"]:
        return
    if "AVALIADOR" in user["perfis"] and await EditalService.usuario_na_comissao(db, inscricao.edital_id, user["id"]):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao titular e à comissão avaliadora.")


@router.get("/me", response_model=List[InscricaoResponse])
async def listar_minhas_inscricoes(
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    inscricoes = await InscricaoService.listar_minhas_inscricoes(db, current_user["id"])
    return [_visao_estudante(i) for i in inscricoes]


@router.get("/{id}", response_model=InscricaoResponse)
async def get_inscricao(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    inscricao = await InscricaoService.get_inscricao_by_id(db, id)
    await _autorizar_leitura(db, inscricao, current_user)
    if inscricao.estudante_id == current_user["id"]:
        return _visao_estudante(inscricao)
    return inscricao


@router.put("/{id}/retificar", response_model=InscricaoResponse)
async def retificar_inscricao(
    id: int, request: Request,
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """Substitui PDFs dentro do prazo de inscrição, mantendo protocolo e dados congelados (INS-05)."""
    form = await ler_formulario(request)
    arquivos = extrair_documentos(form)
    inscricao = await InscricaoService.retificar_inscricao(db, id, current_user["id"], arquivos, get_client_ip(request))
    return _visao_estudante(inscricao)


@router.post("/{id}/desistir", response_model=InscricaoResponse)
async def desistir_inscricao(
    id: int, data: InscricaoDesistirRequest, request: Request,
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    inscricao = await InscricaoService.desistir_inscricao(db, id, current_user["id"], data, get_client_ip(request))
    return _visao_estudante(inscricao)


@router.get("/{id}/comprovante")
async def baixar_comprovante_inscricao(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """Comprovante de inscrição em PDF (INS-04)."""
    inscricao = await InscricaoService.get_inscricao_by_id(db, id)
    if "PRO_REITOR" not in current_user["perfis"] and inscricao.estudante_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao titular da inscrição.")

    nomes_docs = {d.id: d.nome for d in inscricao.edital.documentos_exigidos}
    documentos = [
        f"{nomes_docs.get(a.documento_exigido_id, 'Documento')}: {a.nome_original} (versão {a.versao})"
        for a in sorted(inscricao.arquivos, key=lambda a: (a.documento_exigido_id or 0, a.versao))
        if a.ativo
    ]
    pdf = ReportService.gerar_comprovante_inscricao_pdf(
        protocolo=inscricao.protocolo,
        edital_id=inscricao.edital_id,
        edital_titulo=inscricao.edital.titulo,
        nome=inscricao.estudante.nome,
        matricula=inscricao.estudante.matricula,
        curso=inscricao.curso_congelado,
        cr=inscricao.cr_congelado,
        data_submissao=inscricao.data_submissao_original,
        data_retificacao=inscricao.data_ultima_retificacao,
        situacao=STATUS_INSCRICAO_LABEL.get(inscricao.status, inscricao.status),
        documentos=documentos,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="comprovante_{inscricao.protocolo}.pdf"'},
    )


@router.post("/{id}/reanalisar", response_model=InscricaoResponse)
async def reanalisar_inscricao(
    id: int, data: InscricaoReanalisarRequest, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """Análise manual de inscrições pendentes ou indeferidas, antes da avaliação (RN-05)."""
    return await InscricaoService.reanalisar_inscricao(db, id, data, current_user["id"], get_client_ip(request))


@router.put("/{id}/avaliacao", response_model=AvaliacaoResponse)
async def avaliar_candidatura(
    id: int, data: AvaliacaoInput, request: Request,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await AvaliacaoService.avaliar_inscricao(db, id, current_user["id"], data, get_client_ip(request))


@router.post("/{id}/recursos", response_model=RecursoResponse, status_code=status.HTTP_201_CREATED)
async def interpor_recurso(
    id: int, data: RecursoCreate, request: Request,
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await AvaliacaoService.interpor_recurso(db, id, current_user["id"], data, get_client_ip(request))
