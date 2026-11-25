from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_client_ip, get_password_hash, require_roles
from app.models.user import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioListResponse, UsuarioResponse, UsuarioUpdate
from app.services.audit_service import log_audit_action

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.get("", response_model=UsuarioListResponse)
async def listar_usuarios(
    perfil: Optional[str] = Query(None),
    busca: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db),
):
    filtros = []
    if perfil:
        filtros.append(Usuario.perfil == perfil)
    if busca:
        termo = f"%{busca.strip()}%"
        filtros.append(or_(Usuario.nome.ilike(termo), Usuario.email.ilike(termo), Usuario.matricula.ilike(termo)))
    total = (await db.execute(select(func.count(Usuario.id)).where(*filtros))).scalar() or 0
    items = (await db.execute(
        select(Usuario).where(*filtros).order_by(Usuario.nome.asc()).offset(skip).limit(limit)
    )).scalars().all()
    return UsuarioListResponse(items=list(items), total=total)


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def criar_usuario(
    data: UsuarioCreate, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Cadastro de avaliadores, gestores ou estudantes pela Pró-Reitoria."""
    email = data.email.lower().strip()
    filtros = [func.lower(Usuario.email) == email, Usuario.cpf == data.cpf]
    if data.matricula:
        filtros.append(Usuario.matricula == data.matricula)
    if (await db.execute(select(Usuario.id).where(or_(*filtros)))).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com este e-mail, CPF ou matrícula.")

    user = Usuario(
        nome=data.nome.strip(), email=email, cpf=data.cpf, matricula=data.matricula or None,
        perfil=data.perfil, senha_hash=get_password_hash(data.senha), ativo=True,
    )
    db.add(user)
    await db.flush()
    await log_audit_action(
        db=db, usuario_id=current_user["id"], acao="CRIAR_USUARIO", entidade="usuarios", entidade_id=user.id,
        dados_depois={"email": email, "perfil": data.perfil}, ip_origem=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{id}", response_model=UsuarioResponse)
async def atualizar_usuario(
    id: int, data: UsuarioUpdate, request: Request,
    current_user: dict = Depends(require_roles(["PRO_REITOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Ativa/desativa uma conta ou redefine a senha."""
    user = await db.get(Usuario, id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    if data.ativo is False and user.id == current_user["id"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Você não pode desativar a própria conta.")

    alteracoes = {}
    if data.ativo is not None:
        user.ativo = data.ativo
        alteracoes["ativo"] = data.ativo
    if data.nova_senha:
        user.senha_hash = get_password_hash(data.nova_senha)
        alteracoes["senha_redefinida"] = True

    await log_audit_action(
        db=db, usuario_id=current_user["id"], acao="ATUALIZAR_USUARIO", entidade="usuarios", entidade_id=user.id,
        dados_depois=alteracoes, ip_origem=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(user)
    return user
