from typing import Dict, Any, Optional


class AcademicIntegrationClient:
    """
    Cliente simulado de integração com o Sistema Acadêmico institucional (SisAcad).
    Permite validar vínculo discente, curso matriculado e CR oficial congelado no ato da inscrição (RN-02, RF-17, RF-24).
    """

    MOCK_DISCENTES: Dict[str, Dict[str, Any]] = {
        "estudante@faculdade.edu.br": {
            "matricula": "2024001001",
            "nome": "João Silva",
            "vinculo_ativo": True,
            "curso_codigo": "CC",
            "curso_nome": "Ciência da Computação",
            "semestre_atual": 5,
            "cr_oficial": 8.75,
        },
        "maria.aluna@faculdade.edu.br": {
            "matricula": "2023002002",
            "nome": "Maria Eduarda",
            "vinculo_ativo": True,
            "curso_codigo": "SI",
            "curso_nome": "Sistemas de Informação",
            "semestre_atual": 4,
            "cr_oficial": 7.40,
        },
        "lucas.inativo@faculdade.edu.br": {
            "matricula": "2022003003",
            "nome": "Lucas Trancado",
            "vinculo_ativo": False,
            "curso_codigo": "CC",
            "curso_nome": "Ciência da Computação",
            "semestre_atual": 6,
            "cr_oficial": 5.20,
        }
    }

    @classmethod
    async def consultar_discente(cls, email: str) -> Optional[Dict[str, Any]]:
        """Simula requisição com timeout e fallback (RF-24)."""
        if email in cls.MOCK_DISCENTES:
            return cls.MOCK_DISCENTES[email]

        # Discente padrão fallback
        return {
            "matricula": f"2024{abs(hash(email)) % 900000 + 100000}",
            "nome": email.split("@")[0].replace(".", " ").title(),
            "vinculo_ativo": True,
            "curso_codigo": "CC",
            "curso_nome": "Ciência da Computação",
            "semestre_atual": 3,
            "cr_oficial": 7.50,
        }
