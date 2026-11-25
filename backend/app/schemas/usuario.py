from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.auth import _validar_cpf


class UsuarioCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    cpf: str
    matricula: Optional[str] = Field(None, max_length=40)
    perfil: str
    senha: str = Field(..., min_length=8, max_length=128)

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        return _validar_cpf(v)

    @field_validator("perfil")
    @classmethod
    def validate_perfil(cls, v: str) -> str:
        if v not in ("ESTUDANTE", "AVALIADOR", "PRO_REITOR"):
            raise ValueError("Perfil inválido.")
        return v


class UsuarioUpdate(BaseModel):
    ativo: Optional[bool] = None
    nova_senha: Optional[str] = Field(None, min_length=8, max_length=128)


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    matricula: Optional[str] = None
    perfil: str
    ativo: bool
    criado_em: datetime


class UsuarioListResponse(BaseModel):
    items: List[UsuarioResponse]
    total: int
