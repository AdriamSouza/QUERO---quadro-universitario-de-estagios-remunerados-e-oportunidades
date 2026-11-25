from typing import AsyncIterator
from urllib.parse import quote

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.storage import get_storage_service


def content_disposition(filename: str, inline: bool = False) -> str:
    """Cabeçalho Content-Disposition seguro para nomes com acentos, aspas ou quebras de linha."""
    ascii_name = "".join(c if 32 <= ord(c) < 127 and c not in '"\\' else "_" for c in filename) or "arquivo"
    tipo = "inline" if inline else "attachment"
    return f"{tipo}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


async def stream_arquivo(chave: str, filename: str, media_type: str, inline: bool = False) -> StreamingResponse:
    storage = get_storage_service()
    try:
        stream: AsyncIterator[bytes] = await storage.get_file_stream(chave)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não localizado no armazenamento.")
    return StreamingResponse(
        stream,
        media_type=media_type,
        headers={
            "Content-Disposition": content_disposition(filename, inline),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
