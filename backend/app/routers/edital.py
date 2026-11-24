from fastapi import APIRouter, Depends, Query, Request, status, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict

from app.core.database import get_db
from app.core.security import require_roles, get_current_user
from app.schemas.edital import (
    EditalCreate, EditalUpdate, EditalResponse, EditalListResponse,
    EditalCancelarRequest, ComissaoDesignarRequest, ComissaoEditalResponse
)
from app.schemas.inscricao import InscricaoResponse
from app.schemas.homologacao import ResultadoPreliminarResponse, HomologacaoFinalRequest, DevolverAjustesRequest, AtaHomologacaoResponse
from app.services.edital_service import EditalService
from app.services.inscricao_service import InscricaoService
from app.services.avaliacao_service import AvaliacaoService
from app.services.homologacao_service import HomologacaoService

router = APIRouter(prefix="/editais", tags=["Editais"])


@router.get("", response_model=EditalListResponse)
async def list_editais(
    status: Optional[str] = Query(None, description="Filtrar por status do edital"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria: ESTAGIO, MONITORIA, BOLSA"),
    busca: Optional[str] = Query(None, description="Busca textual por título ou descrição"),
    somente_abertos: bool = Query(False, description="Filtrar apenas editais abertos"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista e filtra editais (v5.0 §11, INS-01).
    Abertos por padrão no portal público se nenhum filtro for especificado.
    """
    items, total = await EditalService.list_editais(
        db=db,
        status_filter=status,
        categoria=categoria,
        search=busca,
        skip=skip,
        limit=limit,
        somente_abertos=somente_abertos
    )
    return EditalListResponse(items=items, total=total)


@router.post("", response_model=EditalResponse, status_code=status.HTTP_201_CREATED)
async def create_edital(
    data: EditalCreate,
    request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria edital em Rascunho com cursos e documentos (v5.0 §11, EDT-01, EDT-02).
    Apenas PRO_REITOR.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await EditalService.create_edital(
        db=db,
        data=data,
        user_id=current_user["id"],
        ip_origem=client_ip
    )


@router.get("/{id}", response_model=EditalResponse)
async def get_edital(id: int, db: AsyncSession = Depends(get_db)):
    """Retorna detalhes do edital por ID."""
    return await EditalService.get_edital_by_id(db, id)


@router.put("/{id}", response_model=EditalResponse)
async def update_edital(
    id: int,
    data: EditalUpdate,
    request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Edita edital (regras restritas se publicado) (v5.0 §11, EDT-01, RN-14).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await EditalService.update_edital(
        db=db,
        edital_id=id,
        data=data,
        user_id=current_user["id"],
        ip_origem=client_ip
    )


@router.post("/{id}/publicar", response_model=EditalResponse)
async def publicar_edital(
    id: int,
    request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Valida cronograma/regras e publica edital (v5.0 §11, EDT-02, EDT-03).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await EditalService.publicar_edital(
        db=db,
        edital_id=id,
        user_id=current_user["id"],
        ip_origem=client_ip
    )


@router.post("/{id}/cancelar", response_model=EditalResponse)
async def cancelar_edital(
    id: int,
    data: EditalCancelarRequest,
    request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancela edital com justificativa e notifica os inscritos (v5.0 §11, EDT-05).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await EditalService.cancelar_edital(
        db=db,
        edital_id=id,
        data=data,
        user_id=current_user["id"],
        ip_origem=client_ip
    )


@router.post("/{id}/comissao", response_model=List[ComissaoEditalResponse])
async def designar_comissao(
    id: int,
    data: ComissaoDesignarRequest,
    request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Designa avaliadores da comissão (bloqueia candidatos do edital) (v5.0 §11, EDT-04, RN-07).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await EditalService.designar_comissao(
        db=db,
        edital_id=id,
        avaliadores_ids=data.avaliadores_ids,
        user_id=current_user["id"],
        ip_origem=client_ip
    )


@router.post("/{id}/inscricoes", response_model=InscricaoResponse, status_code=status.HTTP_201_CREATED)
async def submeter_inscricao(
    id: int,
    request: Request,
    current_user: dict = Depends(require_roles(["ESTUDANTE"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Submete inscrição com upload streaming de PDFs (v5.0 §11, INS-02, INS-03).
    Aceita formulário multipart/form-data com arquivos mapeados por documento exigido.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    form = await request.form()
    arquivos_dict: Dict[int, UploadFile] = {}

    for key, value in form.items():
        if isinstance(value, UploadFile):
            # Procura id numérico no nome do campo (ex: doc_1, documento_2, 3)
            num_part = "".join(filter(str.isdigit, key))
            if num_part:
                arquivos_dict[int(num_part)] = value

    if not arquivos_dict:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhum arquivo enviado no formulário. Envie os arquivos com campos 'doc_{id}'."
        )

    return await InscricaoService.submeter_candidatura(
        db=db,
        edital_id=id,
        estudante_id=current_user["id"],
        estudante_email=current_user["email"],
        arquivos_enviados=arquivos_dict,
        ip_origem=client_ip
    )


@router.get("/{id}/avaliacoes", response_model=List[InscricaoResponse])
async def listar_avaliacoes_edital(
    id: int,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista inscrições homologadas para avaliação pelo membro designado (v5.0 §11, AVA-01, RN-06).
    """
    return await AvaliacaoService.listar_inscricoes_para_avaliacao(
        db=db,
        edital_id=id,
        avaliador_id=current_user["id"]
    )


@router.post("/{id}/resultado-preliminar", response_model=ResultadoPreliminarResponse)
async def publicar_resultado_preliminar(
    id: int,
    request: Request,
    current_user: dict = Depends(require_roles(["AVALIADOR", "PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Calcula classificação, publica resultado preliminar e abre janela de recurso (v5.0 §11, AVA-02, RN-09, RN-10).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await AvaliacaoService.publicar_resultado_preliminar(
        db=db,
        edital_id=id,
        user_id=current_user["id"],
        ip_origem=client_ip
    )


@router.post("/{id}/homologar-final", response_model=AtaHomologacaoResponse)
async def homologar_final(
    id: int,
    data: HomologacaoFinalRequest,
    request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Homologa resultado final, gera ata oficial em PDF e listas em PDF/CSV (v5.0 §11, HOM-01, HOM-02, RN-13).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await HomologacaoService.homologar_final(
        db=db,
        edital_id=id,
        pro_reitor_id=current_user["id"],
        data=data,
        ip_origem=client_ip
    )


@router.post("/{id}/devolver-ajustes", response_model=EditalResponse)
async def devolver_ajustes(
    id: int,
    data: DevolverAjustesRequest,
    request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Devolve processo para EM_AVALIACAO com justificativa obrigatória (v5.0 §11, HOM-01, RN-14).
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await HomologacaoService.devolver_ajustes(
        db=db,
        edital_id=id,
        pro_reitor_id=current_user["id"],
        data=data,
        ip_origem=client_ip
    )
