from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.routers._upload import CAMPO_DOCUMENTO
from app.schemas.auth import CadastroEstudanteRequest
from app.schemas.inscricao import InscricaoReanalisarRequest
from app.services.inscricao_service import _motivos_academicos, _motivos_documentais


def _edital():
    return SimpleNamespace(
        cr_minimo=Decimal("7.00"),
        cursos=[SimpleNamespace(codigo_curso="SI", nome_curso="Sistemas de Informação")],
        documentos_exigidos=[
            SimpleNamespace(id=1, nome="Histórico", obrigatorio=True),
            SimpleNamespace(id=2, nome="Currículo", obrigatorio=False),
        ],
    )


def test_reanalise_exige_justificativa():
    with pytest.raises(ValidationError):
        InscricaoReanalisarRequest(deferido=True, justificativa="Curto")
    req = InscricaoReanalisarRequest(deferido=True, justificativa="Documentação conferida e vínculo comprovado.")
    assert req.deferido is True


def test_motivos_academicos():
    edital = _edital()
    assert _motivos_academicos(edital, True, "SI", Decimal("8.0")) == []
    assert _motivos_academicos(edital, None, "Sistemas de Informação", Decimal("7.0")) == []
    motivos = _motivos_academicos(edital, False, "CC", Decimal("6.5"))
    assert len(motivos) == 3
    assert any("não informado" in m for m in _motivos_academicos(edital, None, "SI", None))


def test_motivos_documentais():
    edital = _edital()
    assert _motivos_documentais(edital, {1}) == []
    assert _motivos_documentais(edital, {2}) == ["Documento obrigatório ausente: Histórico"]


def test_campo_documento_regex():
    assert CAMPO_DOCUMENTO.match("doc_12").group(1) == "12"
    assert CAMPO_DOCUMENTO.match("doc1_2") is None
    assert CAMPO_DOCUMENTO.match("documento_3") is None


def test_cadastro_valida_cpf():
    base = dict(nome="Maria Souza", email="maria@exemplo.edu.br", matricula="2024001", senha="SenhaForte1")
    ok = CadastroEstudanteRequest(cpf="529.982.247-25", **base)
    assert ok.cpf == "52998224725"
    for invalido in ("111.111.111-11", "123", "529.982.247-24"):
        with pytest.raises(ValidationError):
            CadastroEstudanteRequest(cpf=invalido, **base)
    with pytest.raises(ValidationError):
        CadastroEstudanteRequest(cpf="52998224725", **{**base, "senha": "curta"})
