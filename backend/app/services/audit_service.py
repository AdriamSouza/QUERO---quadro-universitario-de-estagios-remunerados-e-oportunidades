from typing import Optional, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.auditoria import AuditoriaLog


async def log_audit_action(
    db: AsyncSession,
    usuario_id: Optional[int],
    acao: str,
    entidade: str,
    entidade_id: int,
    dados_antes: Optional[Dict[str, Any]] = None,
    dados_depois: Optional[Dict[str, Any]] = None,
    ip_origem: Optional[str] = "127.0.0.1",
    **kwargs
) -> AuditoriaLog:
    """
    Grava um registro de auditoria imutável (append-only) no banco relacional (v5.0 §10, RN-14).
    """
    audit_entry = AuditoriaLog(
        usuario_id=usuario_id,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        dados_antes=dados_antes,
        dados_depois=dados_depois,
        ip_origem=ip_origem,
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry
