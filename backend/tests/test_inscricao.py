import pytest
from pydantic import ValidationError
from decimal import Decimal
from app.schemas.inscricao import InscricaoReanalisarRequest, InscricaoDesistirRequest
from app.services.academic_service import AcademicIntegrationClient


def test_reanalise_manual_validations():
    """Valida se o schema de reanálise exige justificativa de ao menos 20 caracteres (RN-05)."""
    with pytest.raises(ValidationError):
        InscricaoReanalisarRequest(deferido=True, justificativa="Curto")

    justificativa_valida = "Candidato comprovou matrícula ativa dentro do período regulamentar."
    req = InscricaoReanalisarRequest(deferido=True, justificativa=justificativa_valida)
    assert req.deferido is True
    assert req.justificativa == justificativa_valida


@pytest.mark.asyncio
async def test_academic_integration_client():
    """Valida resposta do cliente de integração acadêmica (INT-01, RN-02)."""
    discente = await AcademicIntegrationClient.consultar_discente("estudante@faculdade.edu.br")
    assert discente is not None
    assert discente["matricula"] == "2024001001"
    assert discente["vinculo_ativo"] is True
    assert discente["cr_oficial"] == 8.75
