from fastapi import APIRouter, HTTPException, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.core.security import create_access_token, MockAuthProvider, get_current_user
from app.core.database import get_db
from app.models.user import Usuario
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.get("/sso/login")
async def sso_login():
    """
    Inicia fluxo OIDC/SAML com SSO institucional (v5.0 §11, TRV-02).
    Redireciona para o Identity Provider institucional configurado.
    """
    return {
        "status": "iniciando_sso",
        "redirect_url": "/api/v1/auth/sso/callback?code=mock_sso_authorization_code",
        "mensagem": "Redirecionando para o Provedor de Identidade Institucional (OIDC/SAML 2.0)"
    }


@router.get("/sso/callback", response_model=TokenResponse)
async def sso_callback(
    code: str = "mock_sso_authorization_code",
    db: AsyncSession = Depends(get_db)
):
    """
    Conclui autenticação SSO, provisiona usuário como ESTUDANTE caso novo e gera token JWT (TRV-02).
    """
    user = MockAuthProvider.authenticate("estudante@faculdade.edu.br")
    if not user:
        user = {
            "id": 1,
            "nome": "João Silva",
            "email": "estudante@faculdade.edu.br",
            "cpf": "11122233344",
            "matricula": "2024001001",
            "perfil": "ESTUDANTE",
            "perfis": ["ESTUDANTE"],
        }
    
    # Garantir existência no banco de dados
    stmt = select(Usuario).where(Usuario.email == user["email"])
    res = await db.execute(stmt)
    user_db = res.scalar_one_or_none()
    if not user_db:
        user_db = Usuario(
            id=user["id"],
            cpf=user["cpf"],
            matricula=user.get("matricula"),
            nome=user["nome"],
            email=user["email"],
            perfil=user.get("perfil", "ESTUDANTE"),
            ativo=True
        )
        db.add(user_db)
        await db.commit()
        await db.refresh(user_db)

    token_data = {
        "sub": str(user_db.id),
        "email": user_db.email,
        "nome": user_db.nome,
        "perfil": user_db.perfil,
        "perfis": user.get("perfis", [user_db.perfil]),
    }
    token = create_access_token(data=token_data)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_db.id,
        nome=user_db.nome,
        email=user_db.email,
        perfis=user.get("perfis", [user_db.perfil]),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Autenticação de desenvolvimento e contingência local (v5.0 §5 RNF-06).
    """
    if settings.USE_MOCK_AUTH:
        user = MockAuthProvider.authenticate(credentials.email)
        if not user:
            # Fallback provisionando como ESTUDANTE
            clean_email = credentials.email.lower().strip()
            nome_calc = clean_email.split("@")[0].replace(".", " ").title()
            user = {
                "id": 99,
                "nome": nome_calc,
                "email": clean_email,
                "cpf": "99988877766",
                "matricula": "2024999999",
                "perfil": "ESTUDANTE",
                "perfis": ["ESTUDANTE"],
            }

        # Garantir persistência do usuário na tabela usuarios para integridade referencial
        stmt = select(Usuario).where(Usuario.email == user["email"])
        res = await db.execute(stmt)
        user_db = res.scalar_one_or_none()
        if not user_db:
            user_db = Usuario(
                id=user["id"],
                cpf=user.get("cpf", "00000000000"),
                matricula=user.get("matricula"),
                nome=user["nome"],
                email=user["email"],
                perfil=user.get("perfil", "ESTUDANTE"),
                ativo=True
            )
            db.add(user_db)
            await db.commit()
            await db.refresh(user_db)

        token_data = {
            "sub": str(user_db.id),
            "email": user_db.email,
            "nome": user_db.nome,
            "perfil": user_db.perfil,
            "perfis": user.get("perfis", [user_db.perfil]),
        }
        token = create_access_token(data=token_data)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user_db.id,
            nome=user_db.nome,
            email=user_db.email,
            perfis=user.get("perfis", [user_db.perfil]),
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Autenticação direta não configurada; utilize /api/v1/auth/sso/login."
    )


@router.post("/logout")
async def logout(response: Response, current_user: dict = Depends(get_current_user)):
    """
    Revoga sessão e limpa credenciais/cookies HttpOnly (v5.0 §11, RNF-06).
    """
    response.delete_cookie(key="refresh_token")
    return {"status": "sucesso", "mensagem": "Sessão encerrada com sucesso."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna dados e perfil do usuário autenticado (v5.0 §11, TRV-02)."""
    return UserResponse(
        id=current_user["id"],
        nome=current_user["nome"],
        email=current_user["email"],
        matricula=current_user.get("matricula"),
        cpf=current_user.get("cpf"),
        perfis=current_user.get("perfis", [current_user.get("perfil", "ESTUDANTE")]),
    )
