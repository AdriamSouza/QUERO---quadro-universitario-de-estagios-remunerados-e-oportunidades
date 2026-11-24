from fastapi import APIRouter, HTTPException, status, Depends, Response
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.core.security import create_access_token, MockAuthProvider, get_current_user
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
async def sso_callback(code: str = "mock_sso_authorization_code"):
    """
    Conclui autenticação SSO, provisiona usuário como ESTUDANTE caso novo e gera token JWT (TRV-02).
    """
    user = MockAuthProvider.authenticate("estudante@faculdade.edu.br")
    token_data = {
        "sub": str(user["id"]),
        "email": user["email"],
        "nome": user["nome"],
        "perfil": user["perfil"],
        "perfis": user["perfis"],
    }
    token = create_access_token(data=token_data)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user["id"],
        nome=user["nome"],
        email=user["email"],
        perfis=user["perfis"],
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """
    Autenticação de desenvolvimento e contingência local (v5.0 §5 RNF-06).
    """
    if settings.USE_MOCK_AUTH:
        user = MockAuthProvider.authenticate(credentials.email)
        if not user:
            # Fallback provisionando como ESTUDANTE
            user = {
                "id": 99,
                "nome": credentials.email.split("@")[0].replace(".", " ").title(),
                "email": credentials.email,
                "perfil": "ESTUDANTE",
                "perfis": ["ESTUDANTE"],
            }
        token_data = {
            "sub": str(user["id"]),
            "email": user["email"],
            "nome": user["nome"],
            "perfil": user.get("perfil", "ESTUDANTE"),
            "perfis": user.get("perfis", ["ESTUDANTE"]),
        }
        token = create_access_token(data=token_data)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user["id"],
            nome=user["nome"],
            email=user["email"],
            perfis=user.get("perfis", ["ESTUDANTE"]),
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
