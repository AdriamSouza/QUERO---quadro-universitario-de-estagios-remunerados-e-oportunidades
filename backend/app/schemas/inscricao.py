from pydantic import ConfigDict, BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
from decimal import Decimal


class ArquivoResponse(BaseModel):
    id: int
    inscricao_id: Optional[int] = None
    documento_exigido_id: Optional[int] = None
    chave: str
    nome_original: str
    sha256: str
    tamanho_bytes: int
    content_type: str
    versao: int
    ativo: bool
    status_varredura: str
    enviado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class AvaliacaoResumo(BaseModel):
    status: str
    parecer: Optional[str] = None
    nota_merito: Optional[Decimal] = None
    avaliador_id: int


class InscricaoResponse(BaseModel):
    id: int
    protocolo: str
    edital_id: int
    estudante_id: int
    status: str  # 'PENDENTE_VALIDACAO_VINCULO', 'HOMOLOGADA', 'INDEFERIDA', 'DESISTENTE'
    motivos_indeferimento: Optional[List[str]] = None
    vinculo_ativo_congelado: Optional[bool] = None
    curso_congelado: Optional[str] = None
    cr_congelado: Optional[Decimal] = None
    data_submissao_original: datetime
    data_ultima_retificacao: Optional[datetime] = None
    reanalisada_por: Optional[int] = None
    justificativa_reanalise: Optional[str] = None
    arquivos: List[ArquivoResponse] = []
    nome_estudante: Optional[str] = None
    email_estudante: Optional[str] = None
    matricula_estudante: Optional[str] = None
    titulo_edital: Optional[str] = None
    status_edital: Optional[str] = None
    avaliacao_resumo: Optional[AvaliacaoResumo] = None
    recurso_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InscricaoListResponse(BaseModel):
    items: List[InscricaoResponse]
    total: int


class InscricaoReanalisarRequest(BaseModel):
    deferido: bool
    justificativa: str = Field(..., min_length=20, examples=["Candidato apresentou documentação complementar comprovando vínculo e CR regular dentro do prazo."])


class InscricaoDesistirRequest(BaseModel):
    motivo: Optional[str] = Field(None, examples=["Obtenção de outra oportunidade de estágio externo."])
