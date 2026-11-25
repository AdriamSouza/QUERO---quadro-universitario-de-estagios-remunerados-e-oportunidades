from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

import bcrypt
import jwt
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import Usuario

security_bearer = HTTPBearer(auto_error=False)

PERFIS_VALIDOS = ("ESTUDANTE", "AVALIADOR", "PRO_REITOR")


# --------------------------------------------------------------------------
# Senhas (bcrypt direto; passlib não é mais mantido e quebra com bcrypt >= 4.1)
# --------------------------------------------------------------------------
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except ValueError:
        return False


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT assinado com a identificação do usuário."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def usuario_to_dict(user: Usuario) -> Dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "nome": user.nome,
        "matricula": user.matricula,
        "cpf": user.cpf,
        "perfil": user.perfil,
        "perfis": [user.perfil],
    }


_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sessão expirada ou inválida. Entre novamente.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _resolve_user(token: str, db: AsyncSession) -> Dict[str, Any]:
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise _UNAUTHORIZED

    # O perfil e o status vêm sempre do banco: contas desativadas perdem o acesso imediatamente.
    res = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = res.scalar_one_or_none()
    if not user or not user.ativo:
        raise _UNAUTHORIZED
    return usuario_to_dict(user)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Valida o token JWT e carrega o usuário autenticado a partir do banco."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _resolve_user(credentials.credentials, db)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    """Retorna o usuário autenticado, ou None para visitantes (rotas públicas)."""
    if not credentials:
        return None
    try:
        return await _resolve_user(credentials.credentials, db)
    except HTTPException:
        return None


def require_roles(allowed_roles: List[str]):
    """Dependência para autorização baseada em perfis (RBAC)."""
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not any(role in current_user.get("perfis", []) for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil não tem permissão para realizar esta operação.",
            )
        return current_user
    return role_checker


def get_client_ip(request: Request) -> str:
    """IP real do cliente, considerando o proxy reverso do provedor de hospedagem."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return (request.client.host if request.client else "0.0.0.0")[:45]
