import io
import pytest
from fastapi import HTTPException
from app.core.storage import LocalStorageService


@pytest.mark.asyncio
async def test_storage_save_valid_pdf(temp_storage):
    """Testa salvar um arquivo PDF válido com magic bytes %PDF-."""
    service, storage_dir = temp_storage
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    file_obj = io.BytesIO(valid_pdf_content)

    doc_id = "test-doc-001"
    saved_path = await service.save(file_obj, doc_id, "documento.pdf")

    assert saved_path is not None
    assert saved_path.endswith("test-doc-001.pdf")

    # Verifica recuperação
    retrieved = await service.get(doc_id)
    assert retrieved is not None
    content = retrieved.read()
    retrieved.close()
    assert content == valid_pdf_content


@pytest.mark.asyncio
async def test_storage_rejects_invalid_magic_bytes(temp_storage):
    """Testa se arquivos que não iniciam com %PDF- são rejeitados com HTTP 400."""
    service, _ = temp_storage
    invalid_content = b"MZ\x90\x00\x03\x00\x00\x00"  # Executável Windows (MZ)
    file_obj = io.BytesIO(invalid_content)

    with pytest.raises(HTTPException) as exc_info:
        await service.save(file_obj, "malicious", "malicious.pdf")

    assert exc_info.value.status_code == 400
    assert "o documento deve ser um PDF legítimo" in exc_info.value.detail


@pytest.mark.asyncio
async def test_storage_rejects_oversized_file(temp_storage):
    """Testa se arquivos maiores que 10 MB são rejeitados."""
    service, _ = temp_storage
    # 10 MB + 1 byte
    oversized_content = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 10)
    file_obj = io.BytesIO(oversized_content)

    with pytest.raises(HTTPException) as exc_info:
        await service.save(file_obj, "large-doc", "large.pdf")

    assert exc_info.value.status_code == 400
    assert "tamanho máximo" in exc_info.value.detail


@pytest.mark.asyncio
async def test_storage_delete_compensation(temp_storage):
    """Testa exclusão compensatória de arquivos (padrão Unit of Work / SAGA)."""
    service, _ = temp_storage
    valid_pdf_content = b"%PDF-1.7\nExemplo de teste compensatorio"
    file_obj = io.BytesIO(valid_pdf_content)

    doc_id = "temp-rollback-doc"
    await service.save(file_obj, doc_id, "rollback.pdf")

    # Garante que o arquivo existe
    assert await service.get(doc_id) is not None

    # Executa remoção compensatória
    deleted = await service.delete(doc_id)
    assert deleted is True

    # Confirma que foi removido
    assert await service.get(doc_id) is None
