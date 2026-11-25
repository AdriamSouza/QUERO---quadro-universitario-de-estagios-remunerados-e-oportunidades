from pydantic import ConfigDict, BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class AuditoriaLogResponse(BaseModel):
    id: int
    usuario_id: Optional[int] = None
    acao: str
    entidade: str
    entidade_id: int
    dados_antes: Optional[Dict[str, Any]] = None
    dados_depois: Optional[Dict[str, Any]] = None
    ip_origem: Optional[str] = None
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditoriaLogListResponse(BaseModel):
    items: List[AuditoriaLogResponse]
    total: int
