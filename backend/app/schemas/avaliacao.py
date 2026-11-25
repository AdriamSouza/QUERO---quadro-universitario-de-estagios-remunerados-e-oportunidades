from pydantic import ConfigDict, BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


class AvaliacaoInput(BaseModel):
    declaracao_sem_impedimento: bool = Field(..., description="Declaração formal de ausência de impedimento ou suspeição (RN-07)")
    nota_merito: Decimal = Field(..., ge=0, le=10, examples=[8.50], description="Nota de mérito de 0,00 a 10,00 (RN-08)")
    parecer: str = Field(..., examples=["DEFERIDO", "INDEFERIDO"])
    justificativa: Optional[str] = Field(None, description="Obrigatória em caso de parecer INDEFERIDO (RN-08)")
    confirmar: bool = Field(False, description="Se True, confirma a avaliação (status CONFIRMADA); senha salva em RASCUNHO (§7.3)")
    justificativa_retificacao: Optional[str] = Field(None, description="Obrigatória para alterar avaliação previamente confirmada (§7.3)")

    @field_validator("parecer")
    @classmethod
    def validate_parecer(cls, v):
        if v not in ["DEFERIDO", "INDEFERIDO"]:
            raise ValueError("Parecer deve ser 'DEFERIDO' ou 'INDEFERIDO'.")
        return v

    @field_validator("justificativa")
    @classmethod
    def validate_justificativa(cls, v, values):
        parecer = values.data.get("parecer")
        if parecer == "INDEFERIDO" and (not v or len(v.strip()) < 15):
            raise ValueError("Justifique o parecer desfavorável com pelo menos 15 caracteres.")
        return v


class AvaliacaoResponse(BaseModel):
    id: int
    inscricao_id: int
    avaliador_id: int
    declaracao_sem_impedimento: bool
    nota_merito: Optional[Decimal] = None
    parecer: Optional[str] = None
    justificativa: Optional[str] = None
    status: str  # 'RASCUNHO', 'CONFIRMADA', 'RETIFICADA'
    justificativa_retificacao: Optional[str] = None
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)
