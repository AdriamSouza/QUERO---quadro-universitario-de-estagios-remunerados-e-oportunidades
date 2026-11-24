from sqlalchemy import (
    Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class AtaHomologacao(Base):
    __tablename__ = "atas_homologacao"

    id = Column(Integer, primary_key=True, autoincrement=True)
    edital_id = Column(Integer, ForeignKey("editais.id"), nullable=False)
    homologado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    arquivo_pdf_id = Column(Integer, ForeignKey("arquivos.id"), nullable=False)
    arquivo_csv_id = Column(Integer, ForeignKey("arquivos.id"), nullable=False)
    eh_retificacao = Column(Boolean, nullable=False, default=False)
    justificativa_retificacao = Column(Text, nullable=True)
    homologado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relacionamentos
    edital = relationship("Edital", back_populates="atas")
    homologador = relationship("Usuario", foreign_keys=[homologado_por])
    arquivo_pdf = relationship("Arquivo", foreign_keys=[arquivo_pdf_id])
    arquivo_csv = relationship("Arquivo", foreign_keys=[arquivo_csv_id])
