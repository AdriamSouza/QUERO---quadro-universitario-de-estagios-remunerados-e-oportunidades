from pydantic import ConfigDict, BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class ClassificacaoItem(BaseModel):
    posicao: int
    inscricao_id: int
    protocolo: str
    nome_estudante: str
    matricula: Optional[str] = None
    curso: str
    cr: Decimal
    nota_merito: Decimal
    resultado: str  # 'CONTEMPLADO', 'SUPLENTE', 'INDEFERIDO' (RN-12)


class ResultadoPreliminarResponse(BaseModel):
    edital_id: int
    titulo: str
    status_edital: Optional[str] = None
    publicado_em: Optional[datetime] = None
    prazo_recurso_ate: Optional[datetime] = None
    total_homologadas: int
    total_deferidas: int
    total_indeferidas: int
    vagas_totais: int
    contemplados: List[ClassificacaoItem]
    suplentes: List[ClassificacaoItem]
    indeferidos: List[ClassificacaoItem]


class HomologacaoFinalRequest(BaseModel):
    justificativa: Optional[str] = Field(None, examples=["Homologação final do processo seletivo após regular tramitação e julgamento de recursos."])


class DevolverAjustesRequest(BaseModel):
    justificativa: str = Field(..., min_length=15, examples=["Devolvido para a comissão examinadora ajustar notas com base em erro material sanado."])


class AtaHomologacaoResponse(BaseModel):
    id: int
    edital_id: int
    homologado_por: int
    arquivo_pdf_id: int
    arquivo_csv_id: int
    eh_retificacao: bool
    justificativa_retificacao: Optional[str] = None
    homologado_em: datetime

    model_config = ConfigDict(from_attributes=True)
