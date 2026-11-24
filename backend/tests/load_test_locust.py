"""
Teste de Carga e Concorrência Automatizado (RNF-01, RNF-02).
Simula o perfil comportamental de 300 usuários simultâneos no pico de encerramento:
- 60% Leituras do Catálogo e Detalhes de Editais (Meta P95 < 1.5s)
- 30% Consultas ao Painel do Discente e Resultados (Meta P95 < 1.5s)
- 10% Requisições Transacionais de Rascunho e Uploads (Meta P95 < 2.5s)

Como executar:
    locust -f backend/tests/load_test_locust.py --headless -u 300 -r 30 --run-time 15m --host http://localhost:8000
"""

from locust import HttpUser, task, between, tag
import io


class PortalBolsasLoadUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Simula login mock institucional ao iniciar o cliente virtual."""
        res = self.client.post("/api/v1/auth/login", json={"email": "estudante@faculdade.edu.br"})
        if res.status_code == 200:
            token = res.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    # --- 60% Leitura de Editais (P95 < 1.5s) ---
    @tag("leitura")
    @task(6)
    def consultar_catalogo_editais(self):
        self.client.get("/api/v1/editais?status=PUBLICADO_ABERTO&page=1&size=10")

    @tag("leitura")
    @task(3)
    def consultar_detalhes_edital(self):
        self.client.get("/api/v1/editais/1")

    # --- 30% Consultas a Painéis e Status (P95 < 1.5s) ---
    @tag("consultas")
    @task(3)
    def consultar_minhas_inscricoes(self):
        self.client.get("/api/v1/inscricoes/me", headers=self.headers)

    @tag("consultas")
    @task(2)
    def consultar_resultado_preliminar(self):
        self.client.get("/api/v1/editais/1/resultado-preliminar")

    # --- 10% Gravação e Upload Transacional (P95 < 2.5s) ---
    @tag("gravacao")
    @task(1)
    def salvar_rascunho_candidatura(self):
        self.client.post(
            "/api/v1/editais/1/inscricoes/rascunho",
            json={"curso_codigo": "CC", "semestre": 5},
            headers=self.headers
        )
