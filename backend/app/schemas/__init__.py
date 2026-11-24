from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.edital import (
    EditalCreate, EditalUpdate, EditalResponse, EditalListResponse,
    EditalCursoCreate, EditalCursoResponse,
    EditalDocumentoExigidoCreate, EditalDocumentoExigidoResponse,
    ComissaoDesignarRequest, ComissaoEditalResponse, EditalCancelarRequest
)
from app.schemas.inscricao import (
    InscricaoResponse, InscricaoListResponse,
    InscricaoReanalisarRequest, InscricaoDesistirRequest, ArquivoResponse
)
from app.schemas.avaliacao import AvaliacaoInput, AvaliacaoResponse
from app.schemas.recurso import RecursoCreate, RecursoJulgamento, RecursoResponse
from app.schemas.homologacao import (
    ClassificacaoItem, ResultadoPreliminarResponse,
    HomologacaoFinalRequest, DevolverAjustesRequest, AtaHomologacaoResponse
)
from app.schemas.auditoria import AuditoriaLogResponse, AuditoriaLogListResponse
from app.schemas.notificacao import NotificacaoResponse, NotificacaoListResponse

__all__ = [
    "LoginRequest", "TokenResponse", "UserResponse",
    "EditalCreate", "EditalUpdate", "EditalResponse", "EditalListResponse",
    "EditalCursoCreate", "EditalCursoResponse",
    "EditalDocumentoExigidoCreate", "EditalDocumentoExigidoResponse",
    "ComissaoDesignarRequest", "ComissaoEditalResponse", "EditalCancelarRequest",
    "InscricaoResponse", "InscricaoListResponse",
    "InscricaoReanalisarRequest", "InscricaoDesistirRequest", "ArquivoResponse",
    "AvaliacaoInput", "AvaliacaoResponse",
    "RecursoCreate", "RecursoJulgamento", "RecursoResponse",
    "ClassificacaoItem", "ResultadoPreliminarResponse",
    "HomologacaoFinalRequest", "DevolverAjustesRequest", "AtaHomologacaoResponse",
    "AuditoriaLogResponse", "AuditoriaLogListResponse",
    "NotificacaoResponse", "NotificacaoListResponse",
]
