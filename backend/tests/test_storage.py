import pytest
from fastapi import HTTPException

from app.core.storage import validate_pdf_bytes


async def _ler(service, chave: str) -> bytes:
    stream = await service.get_file_stream(chave)
    return b"".join([chunk async for chunk in stream])


async def test_save_and_stream_with_nested_key(temp_storage):
    service, _ = temp_storage
    conteudo = b"%PDF-1.4\n" + b"x" * 200_000  # maior que um bloco de 64 KB
    chave = "editais/1/inscricoes/10/arquivo.pdf"

    await service.save_file_stream(chave, conteudo)
    assert await _ler(service, chave) == conteudo


async def test_csv_keeps_extension(temp_storage):
    service, storage_dir = temp_storage
    await service.save_file_stream("editais/1/atas/lista.csv", "Nome;Nota\r\nJoão;9.5".encode("utf-8"))
    assert (await _ler(service, "editais/1/atas/lista.csv")).decode("utf-8").startswith("Nome;Nota")


async def test_missing_key_raises_file_not_found(temp_storage):
    service, _ = temp_storage
    with pytest.raises(FileNotFoundError):
        await service.get_file_stream("editais/1/nao-existe.pdf")


@pytest.mark.parametrize("chave", ["../fora.pdf", "editais/../../fora.pdf", "/etc/passwd"])
async def test_path_traversal_is_blocked(temp_storage, chave):
    service, _ = temp_storage
    with pytest.raises(ValueError):
        await service.save_file_stream(chave, b"%PDF-1.4")


async def test_delete(temp_storage):
    service, _ = temp_storage
    await service.save_file_stream("a/b.pdf", b"%PDF-1.4")
    assert await service.delete("a/b.pdf") is True
    assert await service.delete("a/b.pdf") is False
    with pytest.raises(FileNotFoundError):
        await service.get_file_stream("a/b.pdf")


async def test_healthcheck(temp_storage):
    service, _ = temp_storage
    assert await service.healthcheck() is True


def test_validate_pdf_bytes():
    validate_pdf_bytes(b"%PDF-1.7 conteudo", "ok.pdf")
    with pytest.raises(HTTPException) as exc:
        validate_pdf_bytes(b"MZ\x90\x00", "virus.pdf")
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException):
        validate_pdf_bytes(b"", "vazio.pdf")
