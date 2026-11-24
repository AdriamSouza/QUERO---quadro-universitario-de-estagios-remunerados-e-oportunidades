from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, TIMESTAMP, ForeignKey,
    UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base


class Edital(Base):
    __tablename__ = "editais"

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=False)
    categoria = Column(String(30), nullable=False)  # 'ESTAGIO', 'MONITORIA', 'BOLSA'
    modalidade = Column(String(50), nullable=False)
    valor_bolsa = Column(Numeric(10, 2), nullable=False)
    carga_horaria_semanal = Column(Integer, nullable=False)
    vagas = Column(Integer, nullable=False)
    cr_minimo = Column(Numeric(4, 2), nullable=False)
    prazo_recurso_horas = Column(Integer, nullable=False, default=48)
    criterios_pontuacao = Column(JSONB, nullable=False, server_default="{}")
    criterios_desempate = Column(JSONB, nullable=False, server_default='["CR_DESC", "SUBMISSAO_ASC"]')
    status = Column(String(30), nullable=False, default="RASCUNHO")

    data_inicio_inscricao = Column(TIMESTAMP(timezone=True), nullable=False)
    data_fim_inscricao = Column(TIMESTAMP(timezone=True), nullable=False)
    data_inicio_avaliacao = Column(TIMESTAMP(timezone=True), nullable=False)
    data_resultado_preliminar = Column(TIMESTAMP(timezone=True), nullable=False)
    data_homologacao_final = Column(TIMESTAMP(timezone=True), nullable=False)

    justificativa_cancelamento = Column(Text, nullable=True)
    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relacionamentos
    criador = relationship("Usuario", foreign_keys=[criado_por], back_populates="editais_criados")
    cursos = relationship("EditalCurso", back_populates="edital", cascade="all, delete-orphan")
    documentos_exigidos = relationship("EditalDocumentoExigido", back_populates="edital", cascade="all, delete-orphan")
    comissao = relationship("ComissaoEdital", back_populates="edital", cascade="all, delete-orphan")
    inscricoes = relationship("Inscricao", back_populates="edital")
    atas = relationship("AtaHomologacao", back_populates="edital")


class EditalCurso(Base):
    __tablename__ = "edital_cursos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    edital_id = Column(Integer, ForeignKey("editais.id", ondelete="CASCADE"), nullable=False)
    codigo_curso = Column(String(40), nullable=False)
    nome_curso = Column(String(120), nullable=False)

    __table_args__ = (
        UniqueConstraint("edital_id", "codigo_curso", name="unq_edital_curso"),
    )

    edital = relationship("Edital", back_populates="cursos")


class EditalDocumentoExigido(Base):
    __tablename__ = "edital_documentos_exigidos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    edital_id = Column(Integer, ForeignKey("editais.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(120), nullable=False)
    descricao = Column(Text, nullable=True)
    obrigatorio = Column(Boolean, nullable=False, default=True)

    edital = relationship("Edital", back_populates="documentos_exigidos")


class ComissaoEdital(Base):
    __tablename__ = "comissao_edital"

    id = Column(Integer, primary_key=True, autoincrement=True)
    edital_id = Column(Integer, ForeignKey("editais.id", ondelete="CASCADE"), nullable=False)
    avaliador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    designado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    designado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("edital_id", "avaliador_id", name="unq_edital_avaliador"),
    )

    edital = relationship("Edital", back_populates="comissao")
    avaliador = relationship("Usuario", foreign_keys=[avaliador_id])
    designador = relationship("Usuario", foreign_keys=[designado_por])
