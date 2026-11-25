import re
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


def _validar_cpf(cpf: str) -> str:
    digits = re.sub(r"\D", "", cpf or "")
    if len(digits) != 11 or digits == digits[0] * 11:
        raise ValueError("CPF inválido.")
    for pos in (9, 10):
        soma = sum(int(digits[i]) * ((pos + 1) - i) for i in range(pos))
        dv = (soma * 10) % 11 % 10
        if dv != int(digits[pos]):
            raise ValueError("CPF inválido.")
    return digits


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(..., min_length=1, max_length=128)


class CadastroEstudanteRequest(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    cpf: str
    matricula: str = Field(..., min_length=3, max_length=40)
    senha: str = Field(..., min_length=8, max_length=128)

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        return _validar_cpf(v)

    @field_validator("nome", "matricula")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


class AlterarSenhaRequest(BaseModel):
    senha_atual: str = Field(..., min_length=1, max_length=128)
    nova_senha: str = Field(..., min_length=8, max_length=128)


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
    perfis: List[str]
