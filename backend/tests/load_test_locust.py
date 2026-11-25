"""
Teste de carga (RNF-01, RNF-02): perfil de 300 usuários simultâneos no pico de encerramento.
- 60% leituras do catálogo e detalhes de editais (meta P95 < 1,5 s)
- 30% consultas ao painel do estudante e ao resultado (meta P95 < 1,5 s)
- 10% downloads de comprovante (meta P95 < 2,5 s)

Pré-requisito: um estudante de teste cadastrado (variáveis LOAD_TEST_EMAIL / LOAD_TEST_SENHA)
e um edital existente (LOAD_TEST_EDITAL_ID).

Como executar (requirements-dev.txt):
    locust -f backend/tests/load_test_locust.py --headless -u 300 -r 30 --run-time 15m --host http://localhost:8000
"""
import os

from locust import HttpUser, between, tag, task

EMAIL = os.getenv("LOAD_TEST_EMAIL", "estudante@faculdade.edu.br")
SENHA = os.getenv("LOAD_TEST_SENHA", "TroqueEstaSenha#2026")
EDITAL_ID = int(os.getenv("LOAD_TEST_EDITAL_ID", "1"))


class PortalEstudanteUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        res = self.client.post("/api/v1/auth/login", json={"email": EMAIL, "senha": SENHA})
        self.headers = {"Authorization": f"Bearer {res.json()['access_token']}"} if res.status_code == 200 else {}
        self.inscricao_id = None
        if self.headers:
            minhas = self.client.get("/api/v1/inscricoes/me", headers=self.headers)
            if minhas.status_code == 200 and minhas.json():
                self.inscricao_id = minhas.json()[0]["id"]

    @tag("leitura")
    @task(6)
    def catalogo(self):
        self.client.get("/api/v1/editais?somente_abertos=true&limit=20", name="/editais")

    @tag("leitura")
    @task(3)
    def detalhe_edital(self):
        self.client.get(f"/api/v1/editais/{EDITAL_ID}", name="/editais/{id}")

    @tag("consultas")
    @task(3)
    def minhas_inscricoes(self):
        self.client.get("/api/v1/inscricoes/me", headers=self.headers)

    @tag("consultas")
    @task(2)
    def resultado(self):
        with self.client.get(
            f"/api/v1/editais/{EDITAL_ID}/resultado-preliminar", name="/editais/{id}/resultado-preliminar",
            catch_response=True,
        ) as res:
            if res.status_code in (200, 404):  # 404 = resultado ainda não publicado
                res.success()

    @tag("downloads")
    @task(1)
    def comprovante(self):
        if self.inscricao_id:
            self.client.get(
                f"/api/v1/inscricoes/{self.inscricao_id}/comprovante", headers=self.headers,
                name="/inscricoes/{id}/comprovante",
            )
