from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sso_sub = Column(String(120), unique=True, nullable=True)
    cpf = Column(String(11), unique=True, nullable=False)
    matricula = Column(String(40), unique=True, nullable=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=True)
    perfil = Column(String(20), nullable=False)  # 'ESTUDANTE', 'AVALIADOR', 'PRO_REITOR'
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relacionamentos
    inscricoes = relationship("Inscricao", foreign_keys="Inscricao.estudante_id", back_populates="estudante")
    editais_criados = relationship("Edital", foreign_keys="Edital.criado_por", back_populates="criador")
    notificacoes = relationship("Notificacao", back_populates="usuario", cascade="all, delete-orphan")
