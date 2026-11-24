# QUERO &mdash; Quadro Universitário de Estágios Remunerados e Oportunidades

> **Sistema Unificado de Seleção e Gestão de Estágios, Monitorias e Bolsas Acadêmicas**  
> Especificação de Requisitos, Modelagem BPMN 2.0, Arquitetura C4 e Engenharia de Software &mdash; **Documento de Projeto Versão 5.0**.

---

## 1. Visão Geral e Identidade do Projeto

O **QUERO** centraliza e digitaliza o ciclo completo das seleções acadêmicas universitárias &mdash; publicação de editais, inscrição com upload em streaming de PDFs, homologação formal automática, avaliação de mérito pela comissão examinadora, interposição e julgamento de recursos, homologação final imutável e geração de atas e folhas de pagamento em PDF/CSV.

### Problemas Solucionados
- **Falta de visibilidade:** O estudante acompanha em tempo real suas candidaturas, notas e resultados pelo painel único do discente.
- **Conferência manual eliminada:** Validação síncrona de vínculo, curso e CR congelado junto ao Sistema Acadêmico (RN-02).
- **Rastreabilidade total:** Trilha de auditoria imutável (*append-only*) em conformidade com a LGPD (RN-14).

---

## 2. Pilha Tecnológica (Stack)

- **Frontend:** TypeScript, React 18, Vite, Tailwind CSS, Lucide Icons.
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (AsyncIO), Alembic, Pydantic v2.
- **Banco de Dados:** PostgreSQL 16 (banco relacional único com sequências atômicas e índices estratégicos).
- **Armazenamento de Arquivos:** `ArmazenamentoDisco` com interface desacoplada compatível com S3 (gravação e leitura em streaming de blocos de 64 KB, limite de 10 MB e validação mágica `%PDF-`).
- **Infraestrutura e Deploy:** Docker Compose para desenvolvimento local; `render.yaml` pronto para deploy automatizado no **Render**.

---

## 3. Modelo de Dados e Arquitetura (v5.0)

O banco de dados relacional é composto estritamente pelas **12 tabelas canônicas** especificadas no §10 do Documento de Projeto v5.0:

1. `usuarios`: Controle unificado de perfis (`ESTUDANTE`, `AVALIADOR`, `PRO_REITOR`).
2. `editais`: Editais parametrizados por categoria (`ESTAGIO`, `MONITORIA`, `BOLSA`), cronograma e critérios de desempate.
3. `edital_cursos`: Cursos de graduação elegíveis por edital.
4. `edital_documentos_exigidos`: Lista de documentos obrigatórios exigidos em PDF.
5. `comissao_edital`: Designação formal de avaliadores por edital (bloqueando candidatos do mesmo edital &mdash; RN-07).
6. `inscricoes`: Candidaturas discentes com protocolo atômico (`QUERO-{edital_id}-{seq}`), dados acadêmicos congelados e estados formais (`PENDENTE_VALIDACAO_VINCULO`, `HOMOLOGADA`, `INDEFERIDA`, `DESISTENTE`).
7. `arquivos`: Metadados e chaves lógicas de PDFs armazenados com hash SHA-256 e status de integridade.
8. `avaliacoes`: Notas de mérito (0,00 a 10,00), pareceres (`DEFERIDO`/`INDEFERIDO`), justificativas e declaração de não-impedimento (RN-07, RN-08).
9. `recursos`: Interposição de recursos em janela regulamentar e julgamento por avaliador distinto (RN-10, RN-11).
10. `atas_homologacao`: Registro definitivo de encerramento pelo Pró-Reitor com vínculo a arquivos oficiais de ata (PDF) e listas (CSV).
11. `notificacoes`: Notificações internas aos candidatos sobre mudanças de status e resultados.
12. `auditoria_logs`: Trilha de auditoria imutável com registro de autor, ação, entidade, data/hora e *diff* de dados (RN-14).

---

## 4. Como Executar Localmente

### Opção A: Execução via Docker Compose (Recomendado)

1. Clone o repositório:
```bash
git clone <URL_DO_REPOSITORIO>
cd SistemasInfo
```

2. Inicialize o ambiente com o Docker Compose:
```bash
docker compose up --build
```

3. Acesse os serviços:
- **Frontend SPA (QUERO):** `http://localhost:3000`
- **Backend API RESTful:** `http://localhost:8000`
- **Documentação Interativa (Swagger/OpenAPI):** `http://localhost:8000/docs`

---

### Opção B: Execução Manual (Sem Docker)

#### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## 5. Deploy no Render

O projeto contém o arquivo de infraestrutura como código `render.yaml` pronto para provisionamento automático no Render:

1. Acesse o painel do [Render](https://dashboard.render.com).
2. Clique em **Blueprints** > **New Blueprint Instance**.
3. Conecte o repositório GitHub `QUERO - quadro universitario de estagios remunerados e oportunidades`.
4. O Render detectará o arquivo `render.yaml` e criará automaticamente:
   - **Banco de Dados PostgreSQL 16 (`quero-db`)**: Serviço de banco gerenciado.
   - **Web Service Backend (`quero-backend`)**: Aplicação FastAPI com execução automática de migrations do Alembic (`alembic upgrade head`) e armazenamento persistente.
   - **Static Site Frontend (`quero-frontend`)**: SPA construída via `npm run build` com regras de reescrita de rotas (`/*` &rarr; `/index.html`) conectada ao backend.

---

## 6. Publicação no GitHub

Para vincular e enviar o repositório local ao GitHub sob o nome solicitado:

```bash
# 1. Crie o repositório no GitHub com o nome:
# "QUERO - quadro universitario de estagios remunerados e oportunidades"

# 2. No terminal local da pasta do projeto:
git init
git add .
git commit -m "feat: implementacao inicial do sistema QUERO conforme Documento de Projeto v5.0"
git branch -M main

# 3. Adicione o remote do seu repositório no GitHub:
git remote add origin https://github.com/<SEU_USUARIO>/QUERO---quadro-universitario-de-estagios-remunerados-e-oportunidades.git

# 4. Envie os commits:
git push -u origin main
```

---

## 7. Licença

Este projeto é desenvolvido para instituições públicas de ensino superior sob licença MIT.
