import pytest
from app.core.security import create_access_token, MockAuthProvider
from jose import jwt
from app.core.config import settings


def test_mock_auth_provider_roles():
    """Valida se os perfis mock atendem aos atores institucionais."""
    student = MockAuthProvider.authenticate("estudante@faculdade.edu.br")
    assert student is not None
    assert "ESTUDANTE" in student["perfis"]

    evaluator = MockAuthProvider.authenticate("avaliador@faculdade.edu.br")
    assert evaluator is not None
    assert "AVALIADOR" in evaluator["perfis"]

    proreitor = MockAuthProvider.authenticate("proreitor@faculdade.edu.br")
    assert proreitor is not None
    assert "PRO_REITOR" in proreitor["perfis"]


def test_jwt_generation_and_claims():
    """Testa geração de token JWT assinado com claims."""
    user_data = {
        "sub": "123",
        "email": "estudante@faculdade.edu.br",
        "nome": "João Silva",
        "perfis": ["ESTUDANTE"]
    }
    token = create_access_token(data=user_data)
    assert isinstance(token, str)

    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "123"
    assert payload["email"] == "estudante@faculdade.edu.br"
    assert "ESTUDANTE" in payload["perfis"]
