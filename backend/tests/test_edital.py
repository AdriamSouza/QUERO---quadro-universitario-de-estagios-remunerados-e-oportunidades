import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.edital import (
    EditalCreate, EditalCursoCreate, EditalDocumentoExigidoCreate
)


def test_edital_create_schema_valid():
    """Valida se o schema do Edital aceita payload correto conforme v5.0 EDT-01, EDT-02."""
    now = datetime.now(timezone.utc)

    payload = {
        "titulo": "Edital 01/2026 - Seleção de Monitoria e Iniciação Científica",
        "descricao": "Processo seletivo para preenchimento de bolsas acadêmicas.",
        "categoria": "MONITORIA",
        "modalidade": "Presencial",
        "valor_bolsa": Decimal("700.00"),
        "carga_horaria_semanal": 20,
        "vagas": 5,
        "cr_minimo": Decimal("6.00"),
        "prazo_recurso_horas": 48,
        "data_inicio_inscricao": now,
        "data_fim_inscricao": now + timedelta(days=5),
        "data_inicio_avaliacao": now + timedelta(days=6),
        "data_resultado_preliminar": now + timedelta(days=10),
        "data_homologacao_final": now + timedelta(days=15),
        "cursos": [
            {"codigo_curso": "CC", "nome_curso": "Ciência da Computação"}
        ],
        "documentos_exigidos": [
            {"nome": "Histórico Escolar", "descricao": "Histórico SIGA", "obrigatorio": True}
        ]
    }

    edital = EditalCreate(**payload)
    assert edital.titulo.startswith("Edital 01/2026")
    assert edital.categoria == "MONITORIA"
    assert edital.vagas == 5
    assert len(edital.cursos) == 1
    assert len(edital.documentos_exigidos) == 1


def test_edital_cronograma_invalido():
    """Valida se o schema rejeita cronograma inválido (fim antes do início - EDT-02)."""
    now = datetime.now(timezone.utc)

    payload = {
        "titulo": "Edital com Cronograma Inválido",
        "descricao": "Teste de validação",
        "categoria": "BOLSA",
        "modalidade": "Presencial",
        "valor_bolsa": Decimal("500.00"),
        "carga_horaria_semanal": 12,
        "vagas": 2,
        "cr_minimo": Decimal("5.00"),
        "data_inicio_inscricao": now,
        "data_fim_inscricao": now - timedelta(days=1),  # Inválido!
        "data_inicio_avaliacao": now + timedelta(days=2),
        "data_resultado_preliminar": now + timedelta(days=5),
        "data_homologacao_final": now + timedelta(days=10),
        "cursos": [{"codigo_curso": "CC", "nome_curso": "Ciência da Computação"}],
        "documentos_exigidos": [{"nome": "Doc", "obrigatorio": True}]
    }

    with pytest.raises(ValidationError):
        EditalCreate(**payload)
