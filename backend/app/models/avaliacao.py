from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, TIMESTAMP,
    ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class Avaliacao(Base):
    __tablename__ = "avaliacoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inscricao_id = Column(Integer, ForeignKey("inscricoes.id"), unique=True, nullable=False)
    avaliador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    declaracao_sem_impedimento = Column(Boolean, nullable=False, default=False)
    nota_merito = Column(Numeric(4, 2), nullable=True)
    parecer = Column(String(20), nullable=True)  # 'DEFERIDO', 'INDEFERIDO'
    justificativa = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="RASCUNHO")  # 'RASCUNHO', 'CONFIRMADA', 'RETIFICADA'
    justificativa_retificacao = Column(Text, nullable=True)
    atualizado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relacionamentos
    inscricao = relationship("Inscricao", back_populates="avaliacao")
    avaliador = relationship("Usuario", foreign_keys=[avaliador_id])
