import re
from typing import Dict

from fastapi import HTTPException, Request, status
from starlette.datastructures import FormData, UploadFile

CAMPO_DOCUMENTO = re.compile(r"^doc_(\d+)$")
MAX_ARQUIVOS_POR_ENVIO = 20


async def ler_formulario(request: Request) -> FormData:
    return await request.form(max_files=MAX_ARQUIVOS_POR_ENVIO, max_fields=50)


def extrair_documentos(form: FormData) -> Dict[int, UploadFile]:
    """Mapeia os campos 'doc_{id}' do formulário multipart para {id_documento_exigido: arquivo}."""
    arquivos: Dict[int, UploadFile] = {}
    for key, value in form.multi_items():
        match = CAMPO_DOCUMENTO.match(key)
        if match and isinstance(value, UploadFile) and value.filename:
            arquivos[int(match.group(1))] = value
    if not arquivos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nenhum arquivo foi enviado. Anexe os documentos em PDF.",
        )
    return arquivos
