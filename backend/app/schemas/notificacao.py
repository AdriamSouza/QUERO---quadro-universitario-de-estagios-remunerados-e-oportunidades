from pydantic import ConfigDict, BaseModel
from typing import List
from datetime import datetime


class NotificacaoResponse(BaseModel):
    id: int
    usuario_id: int
    tipo: str
    titulo: str
    mensagem: str
    lida: bool
    email_status: str
    tentativas_email: int
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificacaoListResponse(BaseModel):
    items: List[NotificacaoResponse]
    total: int
    nao_lidas: int = 0
