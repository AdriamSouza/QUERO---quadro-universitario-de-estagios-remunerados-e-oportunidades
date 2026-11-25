# QUERO — Quadro Universitário de Estágios Remunerados e Oportunidades

> Sistema de seleção e gestão de estágios, monitorias e bolsas acadêmicas.
> Especificação completa em [`docs/`](docs/) (Documento de Projeto v5.0).

---

## 1. Visão geral

O **QUERO** digitaliza o ciclo das seleções acadêmicas: publicação de editais, inscrição com envio de documentos em PDF, conferência pela Pró-Reitoria, avaliação de mérito pela comissão, resultado preliminar, recursos, homologação final com ata em PDF e lista de contemplados em CSV.

### Perfis

| Perfil | Como obtém acesso | O que faz |
|---|---|---|
| **Estudante** | Cadastro próprio na tela *Entrar › Cadastrar* | Inscreve-se, substitui documentos no prazo, acompanha a situação, interpõe recurso |
| **Avaliador(a)** | Cadastrado pela Pró-Reitoria em *Usuários* | Avalia candidaturas dos editais em que integra a comissão, julga recursos |
| **Pró-Reitoria** | Conta da carga inicial ou cadastrada por outro gestor | Cria e publica editais, designa comissões, analisa inscrições, homologa resultados, consulta auditoria |

### Fluxo do edital

```
RASCUNHO → ABERTO → INSCRICOES_ENCERRADAS → EM_AVALIACAO → EM_RECURSO → EM_HOMOLOGACAO_FINAL → ENCERRADO
                                                     ↑__________ devolução para ajustes __________|
```

As transições por prazo (fim das inscrições, início da avaliação, fim da janela de recursos) acontecem **automaticamente** e ficam registradas na auditoria. A Pró-Reitoria também pode encerrar as inscrições antecipadamente.

### Dados acadêmicos

Se `ACADEMIC_API_URL` estiver configurada, vínculo, curso e CR são consultados no sistema acadêmico e a inscrição é homologada automaticamente quando cumpre os requisitos. Sem essa integração, o estudante declara curso e CR, e a inscrição fica **Em análise** até a Pró-Reitoria conferir o histórico enviado (página *Inscrições*).

---

## 2. Tecnologias

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (asyncio), Alembic, Pydantic v2, PyJWT, bcrypt.
- **Banco:** PostgreSQL 16.
- **Documentos:** armazenamento configurável: disco local (`STORAGE_BACKEND=local`) ou PostgreSQL (`STORAGE_BACKEND=database`, usado no Render, cujo disco gratuito é apagado a cada deploy).

---

## 3. Executar localmente

### Opção A — Docker Compose

```bash
cp .env.example .env            # ajuste INITIAL_USERS_PASSWORD
docker compose up --build
```

- Frontend: http://localhost:3000
- API: http://localhost:8000 (documentação em http://localhost:8000/docs)

As migrações rodam na inicialização do backend.

### Opção B — Manual

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\activate
pip install -r requirements-dev.txt
cp ../.env.example .env         # ajuste DATABASE_URL/POSTGRES_* e INITIAL_USERS_PASSWORD
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm ci
npm run dev
```

### Primeiro acesso

A carga inicial cria as contas `proreitor@faculdade.edu.br` (Pró-Reitoria), `avaliador@faculdade.edu.br` e `estudante@faculdade.edu.br`, sem senha. Na inicialização, o backend atribui o valor de **`INITIAL_USERS_PASSWORD`** a todas as contas que ainda não têm senha. Entre com a conta da Pró-Reitoria, troque a senha (menu do usuário › *Alterar senha*) e cadastre os avaliadores reais em *Usuários*. Contas que não serão usadas podem ser desativadas nessa mesma tela.

### Testes

```bash
cd backend && pytest          # testes unitários (storage, PDF/CSV, classificação, segurança)
cd frontend && npm run typecheck
```

---

## 4. Deploy no Render

O `render.yaml` provisiona o banco `quero-db`, a API `quero-backend` e o site `quero-frontend`. A cada push no GitHub o Render refaz o deploy.

1. No painel do Render, abra **quero-backend › Environment** e defina **`INITIAL_USERS_PASSWORD`** (não fica versionada). Sem ela, as contas da carga inicial não conseguem entrar.
2. Se o frontend tiver outro endereço que não `https://quero-frontend.onrender.com`, ajuste `CORS_ORIGINS` no backend e `VITE_API_BASE_URL` no frontend.
3. A migração do banco (`alembic upgrade head`) roda automaticamente no start do backend.

Variáveis principais (ver `.env.example`): `JWT_SECRET_KEY` (gerada pelo Render), `STORAGE_BACKEND=database`, `CORS_ORIGINS`, `ALLOW_STUDENT_SIGNUP`, `ACADEMIC_API_URL` (opcional).

> O plano gratuito do Render hiberna o backend após inatividade; o primeiro acesso pode levar até um minuto.

---

## 5. Licença

MIT.
