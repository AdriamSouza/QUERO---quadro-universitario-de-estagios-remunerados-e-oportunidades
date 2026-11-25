from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token, get_client_ip, get_current_user, get_password_hash, verify_password,
)
from app.models.user import Usuario
from app.schemas.auth import (
    AlterarSenhaRequest, CadastroEstudanteRequest, LoginRequest, TokenResponse, UserResponse,
)
from app.services.audit_service import log_audit_action

router = APIRouter(prefix="/auth", tags=["Autenticação"])

CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="E-mail ou senha incorretos.",
)


def _token_response(user: Usuario) -> TokenResponse:
    token = create_access_token({"sub": str(user.id), "perfil": user.perfil})
    return TokenResponse(
        access_token=token, user_id=user.id, nome=user.nome, email=user.email, perfis=[user.perfil],
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Autenticação por e-mail e senha."""
    email = credentials.email.lower().strip()
    user = (await db.execute(select(Usuario).where(func.lower(Usuario.email) == email))).scalar_one_or_none()
    if not user or not verify_password(credentials.senha, user.senha_hash):
        raise CREDENCIAIS_INVALIDAS
    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta desativada. Procure a Pró-Reitoria.")

    await log_audit_action(
        db=db, usuario_id=user.id, acao="LOGIN", entidade="usuarios", entidade_id=user.id,
        ip_origem=get_client_ip(request),
    )
    await db.commit()
    return _token_response(user)


@router.post("/cadastro", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def cadastrar_estudante(data: CadastroEstudanteRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Cadastro de estudante (perfil ESTUDANTE)."""
    if not settings.ALLOW_STUDENT_SIGNUP:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="O cadastro de novos estudantes está desabilitado.")

    email = data.email.lower().strip()
    conflito = (await db.execute(
        select(Usuario.id).where(or_(
            func.lower(Usuario.email) == email, Usuario.cpf == data.cpf, Usuario.matricula == data.matricula,
        ))
    )).first()
    if conflito:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este e-mail, CPF ou matrícula.",
        )

    user = Usuario(
        nome=data.nome, email=email, cpf=data.cpf, matricula=data.matricula,
        senha_hash=get_password_hash(data.senha), perfil="ESTUDANTE", ativo=True,
    )
    db.add(user)
    await db.flush()
    await log_audit_action(
        db=db, usuario_id=user.id, acao="CADASTRO_ESTUDANTE", entidade="usuarios", entidade_id=user.id,
        dados_depois={"email": email}, ip_origem=get_client_ip(request),
    )
    await db.commit()
    return _token_response(user)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Encerra a sessão. O token é descartado pelo cliente."""
    return {"status": "sucesso", "mensagem": "Sessão encerrada."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"], nome=current_user["nome"], email=current_user["email"],
        matricula=current_user.get("matricula"), perfis=current_user["perfis"],
    )


@router.put("/senha")
async def alterar_senha(
    data: AlterarSenhaRequest, request: Request,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    user = await db.get(Usuario, current_user["id"])
    if not verify_password(data.senha_atual, user.senha_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")
    user.senha_hash = get_password_hash(data.nova_senha)
    await log_audit_action(
        db=db, usuario_id=user.id, acao="ALTERAR_SENHA", entidade="usuarios", entidade_id=user.id,
        ip_origem=get_client_ip(request),
    )
    await db.commit()
    return {"status": "sucesso", "mensagem": "Senha alterada com sucesso."}
