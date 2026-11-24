from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from decimal import Decimal


# --- Cursos ---
class EditalCursoBase(BaseModel):
    codigo_curso: str = Field(..., max_length=40, examples=["CC", "SI", "ENG_SOFT"])
    nome_curso: str = Field(..., max_length=120, examples=["Ciência da Computação"])


class EditalCursoCreate(EditalCursoBase):
    pass


class EditalCursoResponse(EditalCursoBase):
    id: int
    edital_id: int

    class Config:
        from_attributes = True


# --- Documentos Exigidos ---
class EditalDocumentoExigidoBase(BaseModel):
    nome: str = Field(..., max_length=120, examples=["Histórico Escolar Atualizado"])
    descricao: Optional[str] = Field(None, examples=["Histórico oficial com CR emitido pelo SIGA"])
    obrigatorio: bool = True


class EditalDocumentoExigidoCreate(EditalDocumentoExigidoBase):
    pass


class EditalDocumentoExigidoResponse(EditalDocumentoExigidoBase):
    id: int
    edital_id: int

    class Config:
        from_attributes = True


# --- Comissão Avaliadora ---
class ComissaoDesignacaoItem(BaseModel):
    avaliador_id: int


class ComissaoDesignarRequest(BaseModel):
    avaliadores_ids: List[int] = Field(..., min_length=1)


class ComissaoEditalResponse(BaseModel):
    id: int
    edital_id: int
    avaliador_id: int
    avaliador_nome: Optional[str] = None
    avaliador_email: Optional[str] = None
    designado_por: int
    designado_em: datetime

    class Config:
        from_attributes = True


# --- Edital Base e Create ---
class EditalCreate(BaseModel):
    titulo: str = Field(..., max_length=200, examples=["Edital 01/2026 - Seleção de Monitoria e Iniciação Científica"])
    descricao: str = Field(..., examples=["Processo seletivo para preenchimento de bolsas de desenvolvimento acadêmico."])
    categoria: str = Field(..., examples=["ESTAGIO", "MONITORIA", "BOLSA"])
    modalidade: str = Field(..., max_length=50, examples=["Presencial", "Híbrido", "Remoto"])
    valor_bolsa: Decimal = Field(..., ge=0, examples=[700.00])
    carga_horaria_semanal: int = Field(..., gt=0, examples=[20])
    vagas: int = Field(..., gt=0, examples=[5])
    cr_minimo: Decimal = Field(..., ge=0, le=10, examples=[6.00])
    prazo_recurso_horas: int = Field(48, gt=0, examples=[48])
    criterios_pontuacao: Union[Dict[str, Any], List[Any]] = Field(default_factory=dict)
    criterios_desempate: List[str] = Field(default=["CR_DESC", "SUBMISSAO_ASC"])

    data_inicio_inscricao: datetime
    data_fim_inscricao: datetime
    data_inicio_avaliacao: datetime
    data_resultado_preliminar: datetime
    data_homologacao_final: datetime

    cursos: List[EditalCursoCreate] = Field(..., min_length=1)
    documentos_exigidos: List[EditalDocumentoExigidoCreate] = Field(..., min_length=1)

    @field_validator("categoria")
    @classmethod
    def validate_categoria(cls, v):
        if v not in ["ESTAGIO", "MONITORIA", "BOLSA"]:
            raise ValueError("Categoria inválida. Opções: 'ESTAGIO', 'MONITORIA', 'BOLSA'.")
        return v

    @field_validator("data_fim_inscricao")
    @classmethod
    def validate_fim_inscricao(cls, v, values):
        inicio = values.data.get("data_inicio_inscricao")
        if inicio and v <= inicio:
            raise ValueError("data_fim_inscricao deve ser posterior a data_inicio_inscricao.")
        return v

    @field_validator("data_inicio_avaliacao")
    @classmethod
    def validate_inicio_avaliacao(cls, v, values):
        fim_insc = values.data.get("data_fim_inscricao")
        if fim_insc and v < fim_insc:
            raise ValueError("data_inicio_avaliacao deve ser igual ou posterior a data_fim_inscricao.")
        return v

    @field_validator("data_resultado_preliminar")
    @classmethod
    def validate_resultado_preliminar(cls, v, values):
        inicio_av = values.data.get("data_inicio_avaliacao")
        if inicio_av and v < inicio_av:
            raise ValueError("data_resultado_preliminar deve ser posterior ao inicio da avaliacao.")
        return v

    @field_validator("data_homologacao_final")
    @classmethod
    def validate_homologacao_final(cls, v, values):
        res_preliminar = values.data.get("data_resultado_preliminar")
        if res_preliminar and v < res_preliminar:
            raise ValueError("data_homologacao_final deve ser posterior ao resultado preliminar.")
        return v


class EditalUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    modalidade: Optional[str] = None
    valor_bolsa: Optional[Decimal] = None
    carga_horaria_semanal: Optional[int] = None
    vagas: Optional[int] = None
    cr_minimo: Optional[Decimal] = None
    prazo_recurso_horas: Optional[int] = None
    criterios_pontuacao: Optional[Union[Dict[str, Any], List[Any]]] = None
    criterios_desempate: Optional[List[str]] = None
    data_inicio_inscricao: Optional[datetime] = None
    data_fim_inscricao: Optional[datetime] = None
    data_inicio_avaliacao: Optional[datetime] = None
    data_resultado_preliminar: Optional[datetime] = None
    data_homologacao_final: Optional[datetime] = None


class EditalCancelarRequest(BaseModel):
    justificativa: str = Field(..., min_length=15, examples=["Cancelamento motivado por remanejamento orçamentário conforme despacho nº 123/2026."])


class EditalResponse(BaseModel):
    id: int
    titulo: str
    descricao: str
    categoria: str
    modalidade: str
    valor_bolsa: Decimal
    carga_horaria_semanal: int
    vagas: int
    cr_minimo: Decimal
    prazo_recurso_horas: int
    criterios_pontuacao: Union[Dict[str, Any], List[Any]] = {}
    criterios_desempate: List[str] = []
    status: str
    data_inicio_inscricao: datetime
    data_fim_inscricao: datetime
    data_inicio_avaliacao: datetime
    data_resultado_preliminar: datetime
    data_homologacao_final: datetime
    justificativa_cancelamento: Optional[str] = None
    criado_por: int
    criado_em: datetime
    cursos: List[EditalCursoResponse] = []
    documentos_exigidos: List[EditalDocumentoExigidoResponse] = []
    comissao: List[ComissaoEditalResponse] = []

    class Config:
        from_attributes = True


class EditalListResponse(BaseModel):
    items: List[EditalResponse]
    total: int
