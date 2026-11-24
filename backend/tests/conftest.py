import pytest
import os
import shutil
import tempfile
from app.core.storage import LocalStorageService


@pytest.fixture
def temp_storage():
    """Cria um diretório temporário para testes de storage e limpa após execução."""
    temp_dir = tempfile.mkdtemp()
    service = LocalStorageService(storage_dir=temp_dir)
    yield service, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
