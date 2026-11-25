import jwt
import pytest
from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password


def test_password_hash_and_verify():
    hashed = get_password_hash("SenhaForte#2026")
    assert hashed != "SenhaForte#2026"
    assert verify_password("SenhaForte#2026", hashed)
    assert not verify_password("senha-errada", hashed)
    assert not verify_password("qualquer", None)
    assert not verify_password("qualquer", "hash-invalido")


def test_long_password_does_not_crash():
    hashed = get_password_hash("a" * 200)
    assert verify_password("a" * 200, hashed)


def test_jwt_roundtrip():
    token = create_access_token({"sub": "123", "perfil": "ESTUDANTE"})
    payload = decode_access_token(token)
    assert payload["sub"] == "123"
    assert payload["perfil"] == "ESTUDANTE"


def test_jwt_expired_and_tampered():
    expired = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)

    forged = jwt.encode({"sub": "1"}, "outra-chave-qualquer-com-tamanho-suficiente", algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)
