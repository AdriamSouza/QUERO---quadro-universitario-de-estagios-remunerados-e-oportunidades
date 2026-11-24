from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_bearer = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT assinado com claims de usuário e papel."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


class MockAuthProvider:
    """Provedor de autenticação simulada para prototipação e testes locais (v5.0 §2.2)."""
    MOCK_USERS: Dict[str, Dict[str, Any]] = {
        "estudante@faculdade.edu.br": {
            "id": 1,
            "nome": "João Silva",
            "email": "estudante@faculdade.edu.br",
            "matricula": "2024001001",
            "cpf": "11122233344",
            "perfil": "ESTUDANTE",
            "perfis": ["ESTUDANTE"],
        },
        "avaliador@faculdade.edu.br": {
            "id": 2,
            "nome": "Prof. Carlos Avaliador",
            "email": "avaliador@faculdade.edu.br",
            "matricula": "1998002002",
            "cpf": "22233344455",
            "perfil": "AVALIADOR",
            "perfis": ["AVALIADOR"],
        },
        "proreitor@faculdade.edu.br": {
            "id": 3,
            "nome": "Dra. Maria Pró-Reitora",
            "email": "proreitor@faculdade.edu.br",
            "matricula": "1990003003",
            "cpf": "33344455566",
            "perfil": "PRO_REITOR",
            "perfis": ["PRO_REITOR"],
        }
    }

    @classmethod
    def authenticate(cls, email: str) -> Optional[Dict[str, Any]]:
        return cls.MOCK_USERS.get(email)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Dict[str, Any]:
    """Valida o token JWT e extrai o payload do usuário autenticado."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais de autenticação não fornecidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticação inválido.",
            )
        perfil = payload.get("perfil", "ESTUDANTE")
        perfis = payload.get("perfis", [perfil])
        if perfil not in perfis:
            perfis.append(perfil)
        return {
            "id": int(user_id),
            "email": payload.get("email"),
            "nome": payload.get("nome"),
            "matricula": payload.get("matricula"),
            "cpf": payload.get("cpf"),
            "perfil": perfil,
            "perfis": perfis,
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(allowed_roles: List[str]):
    """Dependência para autorização estrita baseada em papéis (RBAC - v5.0 §2.2)."""
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = current_user.get("perfis", [])
        perfil = current_user.get("perfil")
        if perfil and perfil not in user_roles:
            user_roles.append(perfil)
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso não autorizado para o perfil do usuário.",
            )
        return current_user
    return role_checker
