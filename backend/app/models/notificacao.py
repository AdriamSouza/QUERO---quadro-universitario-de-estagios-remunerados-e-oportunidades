from sqlalchemy import (
    Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.models.base import Base


class Notificacao(Base):
    __tablename__ = "notificacoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String(50), nullable=False)
    titulo = Column(String(200), nullable=False)
    mensagem = Column(Text, nullable=False)
    lida = Column(Boolean, nullable=False, default=False)
    email_status = Column(String(20), nullable=False, default="PENDENTE")  # 'PENDENTE', 'ENVIADO', 'FALHA'
    tentativas_email = Column(Integer, nullable=False, default=0)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relacionamentos
    usuario = relationship("Usuario", back_populates="notificacoes")
