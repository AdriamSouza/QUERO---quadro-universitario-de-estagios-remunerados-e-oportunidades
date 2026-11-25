"""
Regras transversais do processo seletivo:
- Transições automáticas de estado do edital baseadas no cronograma (§7.1).
- Classificação (RN-09) e distribuição de vagas (RN-12), usadas no resultado preliminar e na homologação.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.auditoria import AuditoriaLog
from app.models.edital import Edital
from app.models.inscricao import Inscricao

STATUS_INSCRICAO_LABEL = {
    "PENDENTE_VALIDACAO_VINCULO": "Em análise pela Pró-Reitoria",
    "HOMOLOGADA": "Homologada",
    "INDEFERIDA": "Indeferida",
    "DESISTENTE": "Desistente",
}

# (status_origem, status_destino, condição SQL sobre a tabela editais "e")
_TRANSICOES_AUTOMATICAS = [
    ("ABERTO", "INSCRICOES_ENCERRADAS", "e.data_fim_inscricao <= NOW()"),
    ("INSCRICOES_ENCERRADAS", "EM_AVALIACAO", "e.data_inicio_avaliacao <= NOW()"),
    (
        "EM_RECURSO",
        "EM_HOMOLOGACAO_FINAL",
        "e.data_publicacao_preliminar IS NOT NULL "
        "AND e.data_publicacao_preliminar + make_interval(hours => e.prazo_recurso_horas) <= NOW() "
        "AND NOT EXISTS (SELECT 1 FROM recursos r JOIN inscricoes i ON i.id = r.inscricao_id "
        "WHERE i.edital_id = e.id AND r.status IN ('ABERTO', 'EM_ANALISE'))",
    ),
]


async def sincronizar_status_editais(db: AsyncSession) -> None:
    """Aplica as transições de estado vencidas pelo cronograma e registra cada uma na auditoria."""
    alterou = False
    for origem, destino, condicao in _TRANSICOES_AUTOMATICAS:
        res = await db.execute(
            text(
                f"UPDATE editais e SET status = :destino "
                f"WHERE e.status = :origem AND {condicao} RETURNING e.id"
            ),
            {"origem": origem, "destino": destino},
        )
        for (edital_id,) in res.all():
            alterou = True
            db.add(AuditoriaLog(
                usuario_id=None,
                acao="TRANSICAO_AUTOMATICA_EDITAL",
                entidade="editais",
                entidade_id=edital_id,
                dados_antes={"status": origem},
                dados_depois={"status": destino, "motivo": "Prazo do cronograma atingido"},
                ip_origem=None,
            ))
    if alterou:
        await db.commit()


async def get_db_sincronizado(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    """Dependência: sessão de banco com os estados dos editais já atualizados pelo cronograma."""
    await sincronizar_status_editais(db)
    return db


def fim_janela_recurso(edital: Edital) -> Optional[datetime]:
    if not edital.data_publicacao_preliminar:
        return None
    return edital.data_publicacao_preliminar + timedelta(hours=edital.prazo_recurso_horas)


def janela_recurso_aberta(edital: Edital, agora: Optional[datetime] = None) -> bool:
    fim = fim_janela_recurso(edital)
    agora = agora or datetime.now(timezone.utc)
    return edital.status == "EM_RECURSO" and fim is not None and agora < fim


# --------------------------------------------------------------------------
# Classificação (RN-09 / RN-12)
# --------------------------------------------------------------------------
_CRITERIOS_CR = {"CR_DESC", "MAIOR_CR"}
_CRITERIOS_SUBMISSAO = {"SUBMISSAO_ASC", "MENOR_DATA_SUBMISSAO", "ORDEM_INSCRICAO"}


def _chave_ordenacao(insc: Inscricao, criterios: List[str]) -> Tuple:
    nota = insc.avaliacao.nota_merito if insc.avaliacao and insc.avaliacao.nota_merito is not None else Decimal("0")
    cr = insc.cr_congelado if insc.cr_congelado is not None else Decimal("0")
    chave: List[Any] = [-nota]
    for criterio in criterios:
        c = (criterio or "").upper()
        if c in _CRITERIOS_CR:
            chave.append(-cr)
        elif c in _CRITERIOS_SUBMISSAO:
            chave.append(insc.data_submissao_original)
    # Desempates finais sempre aplicados para garantir ordem determinística
    chave.extend([-cr, insc.data_submissao_original, insc.id])
    return tuple(chave)


def classificar(edital: Edital, inscricoes: List[Inscricao]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Recebe inscrições HOMOLOGADAS com avaliação carregada e devolve contemplados, suplentes e indeferidos.
    Os critérios de desempate configurados no edital são respeitados (CR_DESC/MAIOR_CR, SUBMISSAO_ASC).
    """
    criterios = edital.criterios_desempate or ["CR_DESC", "SUBMISSAO_ASC"]
    deferidos = [i for i in inscricoes if i.avaliacao and i.avaliacao.parecer == "DEFERIDO"]
    indeferidos = [i for i in inscricoes if i.avaliacao and i.avaliacao.parecer == "INDEFERIDO"]
    deferidos.sort(key=lambda i: _chave_ordenacao(i, criterios))

    def _item(i: Inscricao, posicao: int, resultado: str) -> Dict[str, Any]:
        return {
            "posicao": posicao,
            "inscricao_id": i.id,
            "protocolo": i.protocolo,
            "nome_estudante": i.estudante.nome if i.estudante else "",
            "matricula": i.estudante.matricula if i.estudante else None,
            "curso": i.curso_congelado or "",
            "cr": i.cr_congelado or Decimal("0.00"),
            "nota_merito": (i.avaliacao.nota_merito if i.avaliacao else None) or Decimal("0.00"),
            "resultado": resultado,
        }

    contemplados, suplentes = [], []
    for pos, insc in enumerate(deferidos, start=1):
        if pos <= edital.vagas:
            contemplados.append(_item(insc, pos, "CONTEMPLADO"))
        else:
            suplentes.append(_item(insc, pos, "SUPLENTE"))

    return {
        "contemplados": contemplados,
        "suplentes": suplentes,
        "indeferidos": [_item(i, 0, "INDEFERIDO") for i in indeferidos],
        "total_deferidos": len(deferidos),
        "total_indeferidos": len(indeferidos),
    }
