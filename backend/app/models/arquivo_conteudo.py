from sqlalchemy import Column, String, LargeBinary, TIMESTAMP, func
from app.models.base import Base


class ArquivoConteudo(Base):
    """Conteúdo binário dos arquivos quando STORAGE_BACKEND=database (hospedagem com disco efêmero)."""
    __tablename__ = "arquivo_conteudos"

    chave = Column(String(255), primary_key=True)
    conteudo = Column(LargeBinary, nullable=False)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
