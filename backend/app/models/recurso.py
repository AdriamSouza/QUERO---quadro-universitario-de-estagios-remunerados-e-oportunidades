from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.models.base import Base, loaded_relationship


class Recurso(Base):
    __tablename__ = "recursos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inscricao_id = Column(Integer, ForeignKey("inscricoes.id"), unique=True, nullable=False)
    texto = Column(Text, nullable=False)
    arquivo_anexo_id = Column(Integer, ForeignKey("arquivos.id"), nullable=True)
    status = Column(String(20), nullable=False, default="ABERTO")  # 'ABERTO', 'EM_ANALISE', 'DEFERIDO', 'INDEFERIDO'
    julgado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    justificativa_decisao = Column(Text, nullable=True)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    julgado_em = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relacionamentos
    inscricao = relationship("Inscricao", back_populates="recurso")
    arquivo_anexo = relationship("Arquivo")
    julgador = relationship("Usuario", foreign_keys=[julgado_por])

    def _insc(self):
        return loaded_relationship(self, "inscricao")

    @property
    def protocolo(self):
        insc = self._insc()
        return insc.protocolo if insc else None

    @property
    def nome_estudante(self):
        insc = self._insc()
        return insc.nome_estudante if insc else None

    @property
    def nota_original(self):
        insc = self._insc()
        av = loaded_relationship(insc, "avaliacao") if insc else None
        return av.nota_merito if av else None

    @property
    def avaliador_original_id(self):
        insc = self._insc()
        av = loaded_relationship(insc, "avaliacao") if insc else None
        return av.avaliador_id if av else None
