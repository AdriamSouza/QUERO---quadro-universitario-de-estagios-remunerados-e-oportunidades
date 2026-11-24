from sqlalchemy import Column, BigInteger, Integer, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base


class AuditoriaLog(Base):
    __tablename__ = "auditoria_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    acao = Column(String(60), nullable=False)
    entidade = Column(String(50), nullable=False)
    entidade_id = Column(Integer, nullable=False)
    dados_antes = Column(JSONB, nullable=True)
    dados_depois = Column(JSONB, nullable=True)
    ip_origem = Column(String(45), nullable=True)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    usuario = relationship("Usuario")
