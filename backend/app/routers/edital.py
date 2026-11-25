from decimal import Decimal, InvalidOperation
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_client_ip, get_optional_user, require_roles
from app.routers._upload import extrair_documentos, ler_formulario
from app.schemas.edital import (
    ComissaoDesignarRequest, ComissaoEditalResponse, EditalCancelarRequest, EditalCreate,
    EditalListResponse, EditalResponse, EditalUpdate,
)
from app.schemas.homologacao import (
    AtaHomologacaoResponse, DevolverAjustesRequest, HomologacaoFinalRequest, ResultadoPreliminarResponse,
)
from app.schemas.inscricao import InscricaoResponse
from app.schemas.recurso import RecursoResponse
from app.services.avaliacao_service import AvaliacaoService
from app.services.edital_service import EditalService
from app.services.homologacao_service import HomologacaoService
from app.services.inscricao_service import InscricaoService
from app.services.workflow_service import get_db_sincronizado

router = APIRouter(prefix="/editais", tags=["Editais"])


def _eh_gestor(user: Optional[dict]) -> bool:
    return bool(user and "PRO_REITOR" in user["perfis"])


def _visao_publica(edital, user: Optional[dict]) -> EditalResponse:
    """Visitantes e estudantes veem os nomes da comissão, mas não os e-mails dos avaliadores."""
    resp = EditalResponse.model_validate(edital)
    if not (user and set(user["perfis"]) & {"PRO_REITOR", "AVALIADOR"}):
        for membro in resp.comissao:
            membro.avaliador_email = None
    return resp


@router.get("", response_model=EditalListResponse)
async def list_editais(
    status: Optional[str] = Query(None, description="Filtrar por status do edital"),
    categoria: Optional[str] = Query(None, description="ESTAGIO, MONITORIA ou BOLSA"),
    busca: Optional[str] = Query(None, description="Busca por título ou descrição"),
    somente_abertos: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: Optional[dict] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """Lista editais. Rascunhos só são visíveis para a Pró-Reitoria."""
    items, total = await EditalService.list_editais(
        db=db, status_filter=status, categoria=categoria, search=busca, skip=skip, limit=limit,
        somente_abertos=somente_abertos, incluir_rascunho=_eh_gestor(user),
    )
    return EditalListResponse(items=[_visao_publica(e, user) for e in items], total=total)


@router.post("", response_model=EditalResponse, status_code=status.HTTP_201_CREATED)
async def create_edital(
    data: EditalCreate, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await EditalService.create_edital(db, data, current_user["id"], get_client_ip(request))


@router.get("/{id}", response_model=EditalResponse)
async def get_edital(
    id: int,
    user: Optional[dict] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    edital = await EditalService.get_edital_by_id(db, id, incluir_rascunho=_eh_gestor(user))
    return _visao_publica(edital, user)


@router.put("/{id}", response_model=EditalResponse)
async def update_edital(
    id: int, data: EditalUpdate, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await EditalService.update_edital(db, id, data, current_user["id"], get_client_ip(request))


@router.post("/{id}/publicar", response_model=EditalResponse)
async def publicar_edital(
    id: int, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await EditalService.publicar_edital(db, id, current_user["id"], get_client_ip(request))


@router.post("/{id}/encerrar-inscricoes", response_model=EditalResponse)
async def encerrar_inscricoes(
    id: int, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await EditalService.encerrar_inscricoes(db, id, current_user["id"], get_client_ip(request))


@router.post("/{id}/cancelar", response_model=EditalResponse)
async def cancelar_edital(
    id: int, data: EditalCancelarRequest, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await EditalService.cancelar_edital(db, id, data, current_user["id"], get_client_ip(request))


# ---------------------------------------------------------------- Comissão
@router.get("/{id}/comissao", response_model=List[ComissaoEditalResponse])
async def listar_comissao(
    id: int,
    current_user: dict = Depends(require_roles(["PRO_REITOR", "AVALIADOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await EditalService.listar_comissao(db, id)


@router.post("/{id}/comissao", response_model=List[ComissaoEditalResponse])
async def designar_comissao(
    id: int, data: ComissaoDesignarRequest, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await EditalService.designar_comissao(db, id, data.avaliadores_ids, current_user["id"], get_client_ip(request))


@router.delete("/{id}/comissao/{avaliador_id}", response_model=List[ComissaoEditalResponse])
async def remover_membro_comissao(
    id: int, avaliador_id: int, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await EditalService.remover_membro_comissao(db, id, avaliador_id, current_user["id"], get_client_ip(request))


# ---------------------------------------------------------------- Inscrições
@router.post("/{id}/inscricoes", response_model=InscricaoResponse, status_code=status.HTTP_201_CREATED)
async def submeter_inscricao(
    id: int, request: Request,
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """
    Submete inscrição (multipart/form-data): arquivos nos campos 'doc_{id}', e opcionalmente
    'curso_codigo' e 'cr_declarado' (usados quando não há integração com o sistema acadêmico).
    """
    form = await ler_formulario(request)
    arquivos = extrair_documentos(form)

    cr_declarado = None
    cr_raw = form.get("cr_declarado")
    if isinstance(cr_raw, str) and cr_raw.strip():
        try:
            cr_declarado = Decimal(cr_raw.replace(",", ".").strip())
        except InvalidOperation:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CR informado é inválido.")
        if not (Decimal("0") <= cr_declarado <= Decimal("10")):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O CR deve estar entre 0 e 10.")
    curso_raw = form.get("curso_codigo")
    curso_codigo = curso_raw.strip() if isinstance(curso_raw, str) and curso_raw.strip() else None

    return await InscricaoService.submeter_candidatura(
        db=db, edital_id=id, estudante=current_user, arquivos_enviados=arquivos,
        curso_codigo=curso_codigo, cr_declarado=cr_declarado, ip_origem=get_client_ip(request),
    )


@router.get("/{id}/inscricoes", response_model=List[InscricaoResponse])
async def listar_inscricoes_edital(
    id: int,
    status_inscricao: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """Todas as inscrições do edital (Pró-Reitoria), com filtro opcional por situação."""
    return await InscricaoService.listar_inscricoes_edital(db, id, status_inscricao)


# ---------------------------------------------------------------- Avaliação e resultado
@router.get("/{id}/avaliacoes", response_model=List[InscricaoResponse])
async def listar_avaliacoes_edital(
    id: int,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """Fila de avaliação: inscrições homologadas, visível apenas aos membros da comissão (AVA-01, RN-07)."""
    return await AvaliacaoService.listar_inscricoes_para_avaliacao(db, id, current_user["id"])


@router.post("/{id}/resultado-preliminar", response_model=ResultadoPreliminarResponse)
async def publicar_resultado_preliminar(
    id: int, request: Request,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await AvaliacaoService.publicar_resultado_preliminar(db, id, current_user, get_client_ip(request))


@router.get("/{id}/resultado-preliminar", response_model=ResultadoPreliminarResponse)
async def consultar_resultado(
    id: int,
    user: Optional[dict] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    """Classificação publicada. A matrícula dos candidatos só é exibida para gestores e avaliadores."""
    interno = bool(user and set(user["perfis"]) & {"PRO_REITOR", "AVALIADOR"})
    return await AvaliacaoService.consultar_resultado(db, id, ocultar_matricula=not interno)


@router.get("/{id}/recursos", response_model=List[RecursoResponse])
async def listar_recursos(
    id: int,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await AvaliacaoService.listar_recursos(db, id, current_user)


# ---------------------------------------------------------------- Homologação
@router.post("/{id}/homologar-final", response_model=AtaHomologacaoResponse)
async def homologar_final(
    id: int, data: HomologacaoFinalRequest, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await HomologacaoService.homologar_final(db, id, current_user["id"], data, get_client_ip(request))


@router.post("/{id}/devolver-ajustes", response_model=EditalResponse)
async def devolver_ajustes(
    id: int, data: DevolverAjustesRequest, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db_sincronizado),
):
    return await HomologacaoService.devolver_ajustes(db, id, current_user["id"], data, get_client_ip(request))
