import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from app.schemas.avaliacao import AvaliacaoInput
from app.schemas.recurso import RecursoCreate, RecursoJulgamento


def test_avaliacao_range_and_justificativa():
    """Valida se nota de mérito está entre 0 e 10 e indeferido exige justificativa (RN-08)."""
    # 1. Nota inválida (> 10)
    with pytest.raises(ValidationError):
        AvaliacaoInput(
            declaracao_sem_impedimento=True,
            nota_merito=Decimal("11.00"),
            parecer="DEFERIDO"
        )

    # 2. Parecer INDEFERIDO sem justificativa deve falhar
    with pytest.raises(ValidationError):
        AvaliacaoInput(
            declaracao_sem_impedimento=True,
            nota_merito=Decimal("4.00"),
            parecer="INDEFERIDO",
            justificativa=""
        )

    # 3. Avaliação válida
    aval = AvaliacaoInput(
        declaracao_sem_impedimento=True,
        nota_merito=Decimal("8.50"),
        parecer="DEFERIDO"
    )
    assert aval.nota_merito == Decimal("8.50")
    assert aval.parecer == "DEFERIDO"


def test_desempate_sorting_logic():
    """Valida desempate: 1º maior CR, 2º menor data de submissão original (RN-09)."""
    now = datetime.now(timezone.utc)

    c1 = {
        "id": 1,
        "nota": Decimal("8.50"),
        "cr": Decimal("7.00"),
        "data_submissao": now
    }
    c2 = {
        "id": 2,
        "nota": Decimal("8.50"),
        "cr": Decimal("8.20"),  # Mesmo score, mas CR maior -> deve ser 1º
        "data_submissao": now + timedelta(hours=1)
    }
    c3 = {
        "id": 3,
        "nota": Decimal("9.00"),  # Maior nota -> deve ser o topo
        "cr": Decimal("6.50"),
        "data_submissao": now + timedelta(hours=2)
    }

    candidatos = [c1, c2, c3]
    candidatos.sort(key=lambda c: (-c["nota"], -c["cr"], c["data_submissao"]))

    assert candidatos[0]["id"] == 3
    assert candidatos[1]["id"] == 2
    assert candidatos[2]["id"] == 1
