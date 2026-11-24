from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, BigInteger, CHAR, TIMESTAMP,
    ForeignKey, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base


class Inscricao(Base):
    __tablename__ = "inscricoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protocolo = Column(String(50), unique=True, nullable=False)
    edital_id = Column(Integer, ForeignKey("editais.id"), nullable=False)
    estudante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    status = Column(String(35), nullable=False)  # 'PENDENTE_VALIDACAO_VINCULO', 'HOMOLOGADA', 'INDEFERIDA', 'DESISTENTE'
    motivos_indeferimento = Column(JSONB, nullable=True)
    vinculo_ativo_congelado = Column(Boolean, nullable=True)
    curso_congelado = Column(String(120), nullable=True)
    cr_congelado = Column(Numeric(4, 2), nullable=True)
    data_submissao_original = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    data_ultima_retificacao = Column(TIMESTAMP(timezone=True), nullable=True)
    reanalisada_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    justificativa_reanalise = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("edital_id", "estudante_id", name="unq_edital_estudante"),
    )

    # Relacionamentos
    edital = relationship("Edital", back_populates="inscricoes")
    estudante = relationship("Usuario", foreign_keys=[estudante_id], back_populates="inscricoes")
    reanalisador = relationship("Usuario", foreign_keys=[reanalisada_por])
    arquivos = relationship("Arquivo", back_populates="inscricao", cascade="all, delete-orphan")
    avaliacao = relationship("Avaliacao", back_populates="inscricao", uselist=False, cascade="all, delete-orphan")
    recurso = relationship("Recurso", back_populates="inscricao", uselist=False, cascade="all, delete-orphan")


class Arquivo(Base):
    __tablename__ = "arquivos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inscricao_id = Column(Integer, ForeignKey("inscricoes.id", ondelete="CASCADE"), nullable=True)
    documento_exigido_id = Column(Integer, ForeignKey("edital_documentos_exigidos.id"), nullable=True)
    chave = Column(String(255), unique=True, nullable=False)
    nome_original = Column(String(255), nullable=False)
    sha256 = Column(CHAR(64), nullable=False)
    tamanho_bytes = Column(BigInteger, nullable=False)
    content_type = Column(String(100), nullable=False, default="application/pdf")
    versao = Column(Integer, nullable=False, default=1)
    ativo = Column(Boolean, nullable=False, default=True)
    status_varredura = Column(String(20), nullable=False, default="VALIDADO")  # 'PENDENTE', 'VALIDADO', 'QUARENTENA', 'REJEITADO'
    enviado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relacionamentos
    inscricao = relationship("Inscricao", back_populates="arquivos")
    documento_exigido = relationship("EditalDocumentoExigido")
