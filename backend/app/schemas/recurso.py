from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


class RecursoCreate(BaseModel):
    texto: str = Field(..., max_length=5000, min_length=20, examples=["Venho interpor recurso em face da nota atribuída ao critério de histórico escolar..."], description="Texto do recurso com até 5000 caracteres (RN-10)")
    arquivo_anexo_id: Optional[int] = Field(None, description="ID do PDF opcional anexado ao recurso (até 10 MB - RN-10)")


class RecursoJulgamento(BaseModel):
    decisao: str = Field(..., examples=["DEFERIDO", "INDEFERIDO"])
    justificativa_decisao: str = Field(..., min_length=20, examples=["Recurso deferido pois a documentação retificada comprovou os requisitos estabelecidos no edital."])
    nova_nota_merito: Optional[Decimal] = Field(None, ge=0, le=10, description="Nova nota de mérito caso recurso seja deferido (AVA-04)")

    @field_validator("decisao")
    @classmethod
    def validate_decisao(cls, v):
        if v not in ["DEFERIDO", "INDEFERIDO"]:
            raise ValueError("Decisão do recurso deve ser 'DEFERIDO' ou 'INDEFERIDO'.")
        return v


class RecursoResponse(BaseModel):
    id: int
    inscricao_id: int
    texto: str
    arquivo_anexo_id: Optional[int] = None
    status: str  # 'ABERTO', 'EM_ANALISE', 'DEFERIDO', 'INDEFERIDO'
    julgado_por: Optional[int] = None
    justificativa_decisao: Optional[str] = None
    criado_em: datetime
    julgado_em: Optional[datetime] = None

    class Config:
        from_attributes = True
