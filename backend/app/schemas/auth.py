from pydantic import BaseModel, EmailStr
from typing import List, Optional


class LoginRequest(BaseModel):
    email: EmailStr
    senha: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    nome: str
    email: str
    perfis: List[str]


class UserResponse(BaseModel):
    id: int
    nome: str
    email: str
    matricula: Optional[str] = None
    cpf: Optional[str] = None
    perfis: List[str]
