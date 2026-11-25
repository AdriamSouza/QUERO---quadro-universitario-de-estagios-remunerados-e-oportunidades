from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.avaliacao import AvaliacaoInput
from app.services.workflow_service import classificar, janela_recurso_aberta


def test_avaliacao_range_and_justificativa():
    with pytest.raises(ValidationError):
        AvaliacaoInput(declaracao_sem_impedimento=True, nota_merito=Decimal("11.00"), parecer="DEFERIDO")
    with pytest.raises(ValidationError):
        AvaliacaoInput(declaracao_sem_impedimento=True, nota_merito=Decimal("4.00"), parecer="INDEFERIDO", justificativa="")
    aval = AvaliacaoInput(declaracao_sem_impedimento=True, nota_merito=Decimal("8.50"), parecer="DEFERIDO")
    assert aval.nota_merito == Decimal("8.50")


def _insc(id_, nota, cr, horas, parecer="DEFERIDO"):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SimpleNamespace(
        id=id_, protocolo=f"QUERO-0001-{id_:05d}", curso_congelado="SI", cr_congelado=Decimal(cr),
        data_submissao_original=base + timedelta(hours=horas),
        estudante=SimpleNamespace(nome=f"Candidato {id_}", matricula=f"M{id_}"),
        avaliacao=SimpleNamespace(nota_merito=Decimal(nota), parecer=parecer),
    )


def test_classificacao_nota_e_desempates():
    edital = SimpleNamespace(vagas=2, criterios_desempate=["CR_DESC", "SUBMISSAO_ASC"])
    inscricoes = [
        _insc(1, "8.50", "7.00", 0),
        _insc(2, "8.50", "8.20", 1),   # mesma nota, CR maior -> à frente do 1
        _insc(3, "9.00", "6.50", 2),   # maior nota -> primeiro
        _insc(4, "8.50", "8.20", 0.5),  # empate em nota e CR com o 2, mas submeteu antes
        _insc(5, "3.00", "9.00", 0, parecer="INDEFERIDO"),
    ]
    res = classificar(edital, inscricoes)
    ordem = [i["inscricao_id"] for i in res["contemplados"] + res["suplentes"]]
    assert ordem == [3, 4, 2, 1]
    assert [i["resultado"] for i in res["contemplados"]] == ["CONTEMPLADO", "CONTEMPLADO"]
    assert [i["posicao"] for i in res["suplentes"]] == [3, 4]
    assert [i["inscricao_id"] for i in res["indeferidos"]] == [5]


def test_classificacao_sem_criterios_configurados_usa_padrao():
    edital = SimpleNamespace(vagas=5, criterios_desempate=["MAIOR_IDADE"])  # critério desconhecido é ignorado
    res = classificar(edital, [_insc(1, "7.0", "6.0", 0), _insc(2, "7.0", "9.0", 5)])
    assert [i["inscricao_id"] for i in res["contemplados"]] == [2, 1]


def test_janela_de_recurso():
    agora = datetime.now(timezone.utc)
    aberto = SimpleNamespace(status="EM_RECURSO", data_publicacao_preliminar=agora - timedelta(hours=1), prazo_recurso_horas=48)
    vencido = SimpleNamespace(status="EM_RECURSO", data_publicacao_preliminar=agora - timedelta(hours=49), prazo_recurso_horas=48)
    sem_data = SimpleNamespace(status="EM_RECURSO", data_publicacao_preliminar=None, prazo_recurso_horas=48)
    assert janela_recurso_aberta(aberto)
    assert not janela_recurso_aberta(vencido)
    assert not janela_recurso_aberta(sem_data)
