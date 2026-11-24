import os
import io
import uuid
import asyncio
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from fastapi import HTTPException, status
from app.core.config import settings

MAGIC_PDF_BYTES = b"%PDF-"


class StorageService(ABC):
    """Interface abstrata de armazenamento de documentos comprobatórios."""

    @abstractmethod
    async def save(self, file_obj: BinaryIO, document_id: str, filename: str) -> str:
        """Grava o fluxo de bytes e retorna o identificador/caminho interno."""
        pass

    @abstractmethod
    async def get(self, document_id: str) -> Optional[BinaryIO]:
        """Recupera o fluxo de bytes para transmissão autorizada ao cliente."""
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Remove o arquivo do armazenamento físico."""
        pass


class LocalStorageService(StorageService):
    """Implementação concreta de armazenamento em sistema de arquivos local persistente."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or settings.STORAGE_PATH
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_file_path(self, document_id: str) -> str:
        # Garante nomeação segura por UUIDv4 isolado
        safe_id = os.path.basename(document_id)
        if not safe_id.endswith(".pdf"):
            safe_id = f"{safe_id}.pdf"
        return os.path.join(self.storage_dir, safe_id)

    async def save(self, file_obj: BinaryIO, document_id: str, filename: str) -> str:
        """
        Grava o stream em disco, validando cabeçalho %PDF- e tamanho máximo (10 MB).
        Executa em chunks para economia de memória primária (RNF-03).
        """
        dest_path = self._get_file_path(document_id)

        # 1. Lê os primeiros bytes para conferência de Magic Bytes
        header = file_obj.read(1024)
        if not header.startswith(MAGIC_PDF_BYTES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo inválido: o documento deve ser um PDF legítimo iniciando com %PDF-."
            )

        total_bytes = len(header)
        if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo excede o tamanho máximo permitido de 10 MB."
            )

        # 2. Escreve em chunks no disco utilizando worker thread não bloqueante
        def _sync_write():
            total = total_bytes
            try:
                with open(dest_path, "wb") as f_out:
                    f_out.write(header)
                    while True:
                        chunk = file_obj.read(65536)  # 64 KB
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > settings.MAX_UPLOAD_SIZE_BYTES:
                            raise ValueError("EXCEEDED_MAX_SIZE")
                        f_out.write(chunk)
            except Exception as ex:
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except OSError:
                        pass
                raise ex

        try:
            await asyncio.to_thread(_sync_write)
        except ValueError as ve:
            if str(ve) == "EXCEEDED_MAX_SIZE":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Arquivo excede o tamanho máximo permitido de 10 MB."
                )
            raise ve

        return dest_path

    async def get(self, document_id: str) -> Optional[BinaryIO]:
        """Recupera o arquivo em disco."""
        file_path = self._get_file_path(document_id)
        if not await asyncio.to_thread(os.path.exists, file_path):
            return None
        return await asyncio.to_thread(open, file_path, "rb")

    async def delete(self, document_id: str) -> bool:
        """Remove o arquivo em disco (utilizado no fluxo compensatório Unit of Work)."""
        file_path = self._get_file_path(document_id)
        def _sync_delete():
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        return await asyncio.to_thread(_sync_delete)


# Singleton do serviço de storage padrão
storage_service: StorageService = LocalStorageService()


def get_storage_service() -> StorageService:
    return storage_service
