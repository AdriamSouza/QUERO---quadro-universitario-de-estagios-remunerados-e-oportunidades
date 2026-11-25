"""
Integração com o Sistema Acadêmico institucional (RN-02, INT-01).

Quando ACADEMIC_API_URL está configurada, o vínculo, o curso e o CR oficial são consultados no
sistema acadêmico e congelados no ato da inscrição. Sem integração configurada (ou se o serviço
estiver indisponível), a inscrição usa os dados declarados pelo estudante e fica com status
PENDENTE_VALIDACAO_VINCULO, aguardando conferência documental pela Pró-Reitoria.
"""
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

ACADEMIC_API_URL = os.getenv("ACADEMIC_API_URL", "").rstrip("/")
ACADEMIC_API_TOKEN = os.getenv("ACADEMIC_API_TOKEN", "")
ACADEMIC_API_TIMEOUT = float(os.getenv("ACADEMIC_API_TIMEOUT", "5"))


class AcademicIntegrationClient:

    @staticmethod
    def configurado() -> bool:
        return bool(ACADEMIC_API_URL)

    @classmethod
    async def consultar_discente(cls, email: str, matricula: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retorna {"matricula", "vinculo_ativo", "curso_codigo", "curso_nome", "cr_oficial"} ou None
        quando a integração não está configurada ou não respondeu.
        """
        if not cls.configurado():
            return None
        headers = {"Authorization": f"Bearer {ACADEMIC_API_TOKEN}"} if ACADEMIC_API_TOKEN else {}
        params = {"email": email}
        if matricula:
            params["matricula"] = matricula
        try:
            async with httpx.AsyncClient(timeout=ACADEMIC_API_TIMEOUT) as client:
                resp = await client.get(f"{ACADEMIC_API_URL}/discentes", params=params, headers=headers)
            if resp.status_code == 404:
                return {"vinculo_ativo": False}
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Sistema acadêmico indisponível: %s", exc)
            return None
