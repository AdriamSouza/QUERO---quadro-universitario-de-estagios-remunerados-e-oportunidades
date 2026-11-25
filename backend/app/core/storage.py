"""
Armazenamento de documentos (PDF/CSV) com interface desacoplada.

- LocalStorageService: grava em disco (indicado para desenvolvimento ou quando há disco persistente).
- DatabaseStorageService: grava o conteúdo no PostgreSQL (tabela arquivo_conteudos). Indicado para
  hospedagens com disco efêmero, como o plano gratuito do Render, onde arquivos em disco são perdidos
  a cada deploy/reinício.
"""
import asyncio
import os
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, select

from app.core.config import settings

MAGIC_PDF_BYTES = b"%PDF-"
CHUNK_SIZE = 64 * 1024  # 64 KB


# --------------------------------------------------------------------------
# Validações de upload
# --------------------------------------------------------------------------
async def read_upload_limited(upload: UploadFile, max_bytes: Optional[int] = None) -> bytes:
    """Lê o upload em blocos, interrompendo assim que o limite de tamanho é ultrapassado."""
    limit = max_bytes or settings.MAX_UPLOAD_SIZE_BYTES
    nome = upload.filename or "arquivo"
    buffer = bytearray()
    while True:
        chunk = await upload.read(CHUNK_SIZE)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"O arquivo '{nome}' excede o tamanho máximo de {limit // (1024 * 1024)} MB.",
            )
    return bytes(buffer)


def validate_pdf_bytes(content: bytes, nome: str = "arquivo") -> None:
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"O arquivo '{nome}' está vazio.")
    if not content.startswith(MAGIC_PDF_BYTES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"O arquivo '{nome}' não é um PDF válido.",
        )
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"O arquivo '{nome}' excede o tamanho máximo permitido.",
        )


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------
class StorageService(ABC):
    """Interface de armazenamento. Arquivos são identificados por uma chave lógica (ex.: editais/1/x.pdf)."""

    @abstractmethod
    async def save_file_stream(self, chave: str, content: bytes) -> None:
        ...

    @abstractmethod
    async def get_file_stream(self, chave: str) -> AsyncIterator[bytes]:
        """Retorna um iterador assíncrono de blocos. Levanta FileNotFoundError se a chave não existir."""
        ...

    @abstractmethod
    async def delete(self, chave: str) -> bool:
        ...

    @abstractmethod
    async def healthcheck(self) -> bool:
        ...


async def _iter_bytes(data: bytes) -> AsyncIterator[bytes]:
    for i in range(0, len(data), CHUNK_SIZE):
        yield data[i:i + CHUNK_SIZE]


# --------------------------------------------------------------------------
# Disco local
# --------------------------------------------------------------------------
class LocalStorageService(StorageService):
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = os.path.realpath(storage_dir or settings.STORAGE_PATH)
        os.makedirs(self.storage_dir, exist_ok=True)

    def _resolve(self, chave: str) -> str:
        """Resolve a chave para um caminho dentro do diretório base (bloqueia path traversal)."""
        if not chave or chave.startswith(("/", "\\")) or "\x00" in chave:
            raise ValueError("Chave de armazenamento inválida.")
        path = os.path.realpath(os.path.join(self.storage_dir, chave))
        if os.path.commonpath([path, self.storage_dir]) != self.storage_dir or path == self.storage_dir:
            raise ValueError("Chave de armazenamento fora do diretório permitido.")
        return path

    async def save_file_stream(self, chave: str, content: bytes) -> None:
        path = self._resolve(chave)

        def _write():
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = f"{path}.part"
            with open(tmp, "wb") as f_out:
                for i in range(0, len(content), CHUNK_SIZE):
                    f_out.write(content[i:i + CHUNK_SIZE])
            os.replace(tmp, path)

        await asyncio.to_thread(_write)

    async def get_file_stream(self, chave: str) -> AsyncIterator[bytes]:
        path = self._resolve(chave)
        if not await asyncio.to_thread(os.path.isfile, path):
            raise FileNotFoundError(chave)

        async def _gen() -> AsyncIterator[bytes]:
            f = await asyncio.to_thread(open, path, "rb")
            try:
                while True:
                    chunk = await asyncio.to_thread(f.read, CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
            finally:
                f.close()

        return _gen()

    async def delete(self, chave: str) -> bool:
        path = self._resolve(chave)

        def _delete() -> bool:
            if os.path.isfile(path):
                os.remove(path)
                return True
            return False

        return await asyncio.to_thread(_delete)

    async def healthcheck(self) -> bool:
        def _check() -> bool:
            test_file = os.path.join(self.storage_dir, ".healthcheck")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return True

        try:
            return await asyncio.to_thread(_check)
        except OSError:
            return False


# --------------------------------------------------------------------------
# PostgreSQL
# --------------------------------------------------------------------------
class DatabaseStorageService(StorageService):
    """Persiste o conteúdo dos arquivos na tabela arquivo_conteudos."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    @property
    def session_factory(self):
        if self._session_factory is None:
            from app.core.database import AsyncSessionLocal
            self._session_factory = AsyncSessionLocal
        return self._session_factory

    async def save_file_stream(self, chave: str, content: bytes) -> None:
        from app.models.arquivo_conteudo import ArquivoConteudo
        async with self.session_factory() as session:
            existente = await session.get(ArquivoConteudo, chave)
            if existente:
                existente.conteudo = content
            else:
                session.add(ArquivoConteudo(chave=chave, conteudo=content))
            await session.commit()

    async def get_file_stream(self, chave: str) -> AsyncIterator[bytes]:
        from app.models.arquivo_conteudo import ArquivoConteudo
        async with self.session_factory() as session:
            res = await session.execute(select(ArquivoConteudo.conteudo).where(ArquivoConteudo.chave == chave))
            data = res.scalar_one_or_none()
        if data is None:
            raise FileNotFoundError(chave)
        return _iter_bytes(bytes(data))

    async def delete(self, chave: str) -> bool:
        from app.models.arquivo_conteudo import ArquivoConteudo
        async with self.session_factory() as session:
            res = await session.execute(delete(ArquivoConteudo).where(ArquivoConteudo.chave == chave))
            await session.commit()
            return (res.rowcount or 0) > 0

    async def healthcheck(self) -> bool:
        return True  # depende apenas do banco, verificado separadamente


def _build_storage() -> StorageService:
    if settings.STORAGE_BACKEND == "database":
        return DatabaseStorageService()
    return LocalStorageService()


storage_service: StorageService = _build_storage()


def get_storage_service() -> StorageService:
    return storage_service
