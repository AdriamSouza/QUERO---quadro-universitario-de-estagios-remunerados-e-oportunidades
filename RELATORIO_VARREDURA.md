# Relatório de Varredura — QUERO (Portal de Estágios e Bolsas)

**Data:** 25/11/2026
**Escopo:** backend (FastAPI/SQLAlchemy), frontend (React/Vite), infraestrutura (Docker, Render), testes.
**Método:** leitura do código-fonte. Os testes **não foram executados** porque o ambiente local não tem `pytest` nem `node_modules` instalados. Os itens marcados como ✅ *confirmado* foram verificados diretamente no código; os demais são riscos ou melhorias.

---

## ✅ Situação após a atualização de 25/11/2026

**Corrigidos:**
- **Críticos:** C1 a C6, todos.
- **Alta severidade:** A1 a A12, todos.
- **Média severidade:** M1 a M15, todos.

Também foram resolvidos a maior parte dos itens das seções 4 a 8. A tabela abaixo resume o que mudou.

| Área | O que mudou |
|---|---|
| Autenticação | O login simulado foi removido. O acesso agora é por e-mail e senha (bcrypt + PyJWT) e há cadastro próprio de estudantes. A Pró-Reitoria gerencia usuários em *Usuários*. O perfil é lido do banco a cada requisição e contas desativadas perdem o acesso imediatamente. As contas da carga inicial recebem a senha de `INITIAL_USERS_PASSWORD`. |
| Fluxo do edital | Transições automáticas por prazo foram implementadas (registradas na auditoria). A Pró-Reitoria pode encerrar as inscrições manualmente. A janela de recurso agora é aplicada de fato, e o desempate segue os critérios configurados no edital. |
| Armazenamento | Foram criados os métodos `save_file_stream`/`get_file_stream` e o backend `database`, que guarda os documentos no PostgreSQL e evita a perda de arquivos no Render. Também há proteção contra path traversal e compensação de arquivos órfãos. |
| Dados acadêmicos | O mock que aceitava qualquer aluno foi removido. A integração real fica opcional via `ACADEMIC_API_URL`. Sem ela, o estudante declara curso e CR e a inscrição fica *Em análise* até a Pró-Reitoria conferir. |
| Relatórios | O PDF agora é válido (xref correto, várias páginas, acentos). O CSV usa o módulo `csv`, com BOM e proteção contra fórmulas. O nome de arquivo no download passou a ser seguro. |
| Frontend | O simulador de perfis foi removido. Foram criados: tela de login/cadastro; páginas de *Inscrições*, *Recursos*, *Usuários*; gestão do edital (publicar, encerrar, cancelar, comissão); notificações; troca de senha; tratamento de sessão expirada; toasts no lugar de `alert()`; rótulos de status legíveis; TypeScript `strict`. |
| Infra | `render.yaml` foi revisado (sem mock, CORS restrito, storage no banco, healthcheck). O Dockerfile não usa mais `--reload` e roda com usuário não-root. O Compose ganhou migrações automáticas e volume correto. `requirements-dev.txt` foi criado. |
| Testes | 29 testes unitários, mais um roteiro de ponta a ponta (57 verificações, todas aprovadas) executado contra PostgreSQL 16 real. |

**Pendentes (não incluídos nesta rodada):**
- Pipeline de CI no GitHub Actions.
- Roteamento por URL no frontend (`react-router`).
- Token em cookie `HttpOnly` em vez de `localStorage`.
- Envio de notificações por e-mail.
- Antivírus nos uploads.
- SSO institucional (OIDC).
- Testes automatizados de integração versionados no repositório.

---

## Sumário executivo (análise original)

| Severidade | Qtde | Resumo |
|---|---|---|
| 🔴 Crítico (quebra funcionalidade ou segurança grave) | 6 | Métodos de storage inexistentes, fluxo de estados travado, login aberto em produção, falha ao criar 2º usuário novo |
| 🟠 Alto | 12 | Falhas de autorização, regras de negócio (RN) burladas, arquivos órfãos, CSV/PDF malformados |
| 🟡 Médio | 15 | Inconsistências, paginação incorreta, campos nunca preenchidos, UX |
| 🔵 Baixo / Melhorias | 20+ | Qualidade de código, DevOps, testes, documentação |

**Os três primeiros itens críticos (C1, C2, C3) impedem o fluxo principal do sistema** (inscrição → avaliação → homologação → download) de funcionar de ponta a ponta. Devem ser corrigidos antes de qualquer outra coisa.

---

## 🔴 1. Críticos

### C1. `save_file_stream` / `get_file_stream` não existem no serviço de storage ✅ *confirmado*
- `LocalStorageService` (`backend/app/core/storage.py`) implementa só `save`, `get` e `delete`.
- O código chama métodos que não existem:
  - `backend/app/services/inscricao_service.py:164` e `:273`: `storage.save_file_stream(...)`
  - `backend/app/services/homologacao_service.py:140` e `:155`: `storage.save_file_stream(...)`
  - `backend/app/routers/documento.py:72`, `backend/app/routers/homologacao.py:36` e `:66`: `storage.get_file_stream(...)`
- **Impacto:** **toda** inscrição com arquivo, retificação, homologação final e download de documento/ata/CSV termina em `AttributeError` → HTTP 500.
- **Correção:** adicionar ao `StorageService` (abstrato) e ao `LocalStorageService`:
  - `async def save_file_stream(self, chave: str, content: bytes) -> str`, que aceite chaves com subdiretórios (`editais/1/inscricoes/...`): hoje `_get_file_path` usa `os.path.basename`, o que achata o caminho, e força a extensão `.pdf`, o que quebra o `.csv`.
  - `def get_file_stream(self, chave: str) -> Iterator[bytes]`: gerador em blocos de 64 KB que levanta `FileNotFoundError`.
  - Validar que o caminho final resolvido continua dentro de `storage_dir` (proteção contra *path traversal*).
  - Criar testes unitários para os dois métodos.

### C2. Máquina de estados do edital nunca sai de `ABERTO` ✅ *confirmado*
- Nada no código faz a transição `ABERTO → INSCRICOES_ENCERRADAS`, nem por job/agendador nem por endpoint.
- `avaliacao_service.py:86` só aceita avaliação com o edital em `INSCRICOES_ENCERRADAS` ou `EM_AVALIACAO`.
- **Impacto:** nenhuma avaliação consegue ser lançada, e por isso resultado preliminar, recursos e homologação ficam inalcançáveis.
- **Correção (escolher uma):**
  1. Transição "preguiçosa": ao carregar o edital, se `status == ABERTO` e `now > data_fim_inscricao`, mudar para `INSCRICOES_ENCERRADAS`.
  2. Endpoint `POST /editais/{id}/encerrar-inscricoes` (PRO_REITOR).
  3. Job agendado (APScheduler/cron) que encerra editais vencidos.
- Centralizar as transições em um único módulo (`edital_state_machine.py`) com a tabela de transições permitidas.

### C3. Login mock habilitado em produção = qualquer pessoa vira Pró-Reitor ✅ *confirmado*
- `render.yaml:34-35` define `USE_MOCK_AUTH=true` no deploy de produção.
- `POST /auth/login` (`routers/auth.py:82`) recebe **apenas o e-mail, sem senha**. Enviar `proreitor@faculdade.edu.br` gera um token de PRO_REITOR.
- O frontend ainda faz **login automático** como estudante ao abrir a página (`AuthContext.tsx`, `initAuth`).
- **Correção:**
  - Em `ENVIRONMENT=production`, recusar a inicialização se `USE_MOCK_AUTH=true` (validação no `Settings`).
  - Implementar SSO real (OIDC) ou, no mínimo, login com senha (`senha_hash` já existe na tabela, e `verify_password` já existe em `security.py`).
  - Se o deploy for apenas de demonstração, deixar isso explícito no README e na tela de login.

### C4. Segundo usuário "novo" no login mock quebra com erro 500 ✅ *confirmado*
- `routers/auth.py:96-101`: todo e-mail desconhecido é criado com **`id=99`** e **`cpf="99988877766"`** fixos.
- O primeiro e-mail novo funciona. O segundo viola a PK/UNIQUE e gera `IntegrityError` → HTTP 500.
- **Correção:** não definir `id` manualmente (deixar o `SERIAL` gerar). Gerar CPF/matrícula placeholders únicos ou tornar `cpf` *nullable* para usuários mock. Envolver a criação em `try/except IntegrityError`.

### C5. Segredo JWT padrão conhecido
- `core/config.py:22` usa um `JWT_SECRET_KEY` padrão hard-coded, que também aparece em `.env.example`. No Render é gerado (`generateValue: true`), mas qualquer ambiente sem `.env` usa a chave pública.
- **Correção:** em produção, falhar na inicialização se a chave for a padrão ou tiver menos de 32 bytes.

### C6. CORS `*` combinado com `allow_credentials=True`
- `main.py:68-74` e `render.yaml:33`. Navegadores rejeitam essa combinação para requisições com credenciais, e a configuração indica que não há restrição real de origem.
- **Correção:** em produção, definir `CORS_ORIGINS=https://quero-frontend.onrender.com`. Usar `allow_credentials=False` se não houver cookies (hoje o token vai no header).

---

## 🟠 2. Alta severidade

### Autorização / LGPD
| # | Local | Problema | Correção |
|---|---|---|---|
| A1 | `routers/inscricao.py:43-45` | **Qualquer** AVALIADOR vê qualquer inscrição (dados pessoais, CR, arquivos), mesmo sem estar na comissão do edital. | Verificar `ComissaoEdital` igual a `documento.py` já faz. |
| A2 | `services/avaliacao_service.py:373` (`julgar_recurso`) | Não verifica se o julgador pertence à comissão do edital. Qualquer AVALIADOR julga qualquer recurso. | Checar comissão (exceto PRO_REITOR). |
| A3 | `services/avaliacao_service.py:350-353` | `arquivo_anexo_id` do recurso aceita **qualquer ID de arquivo**, inclusive de outro candidato. | Validar que o arquivo pertence à inscrição do próprio estudante. |
| A4 | `services/avaliacao_service.py:147` | Outro membro da comissão pode sobrescrever a avaliação já feita (troca `avaliador_id`). | Bloquear ou exigir retificação explícita, auditando o avaliador anterior. |
| A5 | `routers/homologacao.py` | Ata e CSV são públicos (sem autenticação) e trazem nome + matrícula + CR + nota. | Avaliar com o requisito LGPD (RN-14/15): mascarar a matrícula ou exigir login para o CSV. |
| A6 | `core/security.py:70` | O token não é revalidado contra o banco: usuário desativado (`ativo=False`) continua com acesso até o token expirar (120 min). O logout não revoga nada. | Consultar `ativo` em `get_current_user` (ou usar tokens curtos + refresh) e manter uma *deny-list* no logout. |

### Regras de negócio
| # | Local | Problema | Correção |
|---|---|---|---|
| A7 | `avaliacao_service.py:277` + `homologacao_service.py:44` | A janela de recurso (`prazo_recurso_horas`, RN-10) **não é aplicada**: não há registro da data de abertura, e a homologação aceita edital em `EM_RECURSO` imediatamente. | Gravar `data_publicacao_preliminar`, bloquear recursos após o prazo e bloquear a homologação antes do fim da janela. |
| A8 | `inscricao_service.py:293-296` | A retificação muda `INDEFERIDA → HOMOLOGADA` verificando só vínculo e CR, **ignorando o curso não elegível e documentos obrigatórios ainda ausentes**. | Reexecutar a validação completa (reaproveitar a lógica de `submeter_candidatura`). |
| A9 | `inscricao_service.py:149` | `doc_id` vindo do formulário não é validado contra os documentos **deste** edital. Aceita qualquer ID, inclusive de outro edital (FK válida). | Recusar IDs fora de `edital.documentos_exigidos`. |
| A10 | `inscricao_service.py:362` | A reanálise permite qualquer status de inscrição (ex.: reverter `DESISTENTE`) e a lista de estados bloqueados não inclui `EM_RECURSO`, `EM_HOMOLOGACAO_FINAL` nem `CANCELADO`. | Permitir só `INDEFERIDA`/`PENDENTE_VALIDACAO_VINCULO` e usar uma lista de estados permitidos (allow-list). |
| A11 | `edital_service.py:164-175` | Um edital publicado ainda aceita alterar `data_inicio_avaliacao`, `data_resultado_preliminar`, `categoria`, `carga_horaria`, `prazo_recurso_horas` etc. O `EditalUpdate` não tem nenhum validador (categoria, faixas, ordem do cronograma). | Allow-list de campos editáveis após a publicação. Validar o cronograma resultante. |

### Integridade de dados
| # | Local | Problema | Correção |
|---|---|---|---|
| A12 | `inscricao_service.py:143-200` | Os arquivos são gravados em disco **antes** do commit. Se um arquivo posterior falhar (PDF inválido/grande), o banco faz rollback mas os arquivos anteriores ficam **órfãos**. O docstring de `storage.delete` cita "Unit of Work" mas nunca é usado. | Validar todos os arquivos antes, gravar depois e, em `except`, apagar as chaves já salvas (`salvos` já existe para isso). |

---

## 🟡 3. Média severidade

### Backend
- **M1** `routers/homologacao.py:31,61`: `scalar_one_or_none()` em uma consulta que pode retornar várias atas (retificação) gera `MultipleResultsFound` (500). Usar `.limit(1)` + `scalars().first()`.
- **M2** `routers/notificacao.py:55-59`: se a notificação não existe, retorna `None` com `response_model`, o que gera erro de validação (500). Levantar 404.
- **M3** `edital_service.py:138-145`: a contagem `total` ignora o filtro `busca`, e a paginação fica errada.
- **M4** `edital_service.py:259` (`cancelar_edital`): o docstring diz "notifica os inscritos", mas nenhuma notificação é criada. Também permite cancelar um edital já `CANCELADO`.
- **M5** `edital_service.py:292` (`designar_comissao`): não valida se os IDs existem nem se têm perfil `AVALIADOR`. Um ID inexistente gera `IntegrityError` (500).
- **M6** `homologacao_service.py:200`: `ata.id` é usado na auditoria **antes** do `flush`, então é gravado como `None`.
- **M7** `criterios_desempate` é salvo no edital mas **ignorado**: o desempate está fixo em CR desc + data asc (`avaliacao_service.py:231`, `homologacao_service.py:78`). A lógica de ranking também está duplicada nos dois serviços. Extrair para uma função única que respeite o critério configurado.
- **M8** Corridas de concorrência: a inscrição dupla simultânea dispara a `UniqueConstraint` → `IntegrityError` (500 em vez de 409). Tratar a exceção.
- **M9** `inscricao_service.py:80-81`: o fallback do protocolo usa `timestamp`, o que pode gerar colisões e mascara erro de banco. Melhor falhar.
- **M10** `ComissaoEditalResponse.avaliador_nome/email` e `InscricaoResponse.nome_estudante/email_estudante/titulo_edital` **nunca são preenchidos** (não existem como atributos no model), então o frontend sempre recebe `null`. Usar `@property` nos models ou montar a resposta explicitamente.
- **M11** `academic_service.py:48`: `hash(email)` varia entre execuções (hash randomization), então a matrícula "mock" muda a cada restart. Além disso, **qualquer e-mail desconhecido é considerado aluno ativo com CR 7.50**.
- **M12** `report_service.py:29-43`: o CSV não escapa `;`, aspas nem quebras de linha nos nomes/cursos, e não protege contra *CSV injection* (`=`, `+`, `-`, `@`). Usar o módulo `csv` com `quoting=csv.QUOTE_MINIMAL` e prefixar `'` em células perigosas. Incluir BOM UTF-8 para abrir corretamente no Excel.
- **M13** PDFs gerados manualmente (`report_service.py`, `routers/inscricao.py:139-159`):
  - A tabela `xref` declara 6 objetos mas lista só 1 (PDF inválido, que o leitor "repara").
  - O comprovante **não escapa** `(`, `)` e `\` (a ata escapa). Um nome com parênteses quebra o PDF.
  - Página única: listas longas ultrapassam a página e o texto some.
  - Acentos são substituídos por `?` (latin-1 com `errors="replace"`, que funciona só parcialmente).
  - **Recomendação:** usar `reportlab` ou `fpdf2` e centralizar a geração do comprovante no `ReportService`.
- **M14** `routers/documento.py:83`: `nome_original` (vindo do usuário) vai direto para `Content-Disposition`. Caracteres não latin-1 ou aspas quebram o header. Usar `filename*=UTF-8''<urlencoded>`.

### Frontend
- **M15** `DocumentReviewPage.tsx:39` usa `/editais/{id}/avaliacoes`, que (a) retorna **apenas inscrições HOMOLOGADAS** e (b) exige que o usuário esteja na comissão, dando 403 para o Pró-Reitor. A tela de reanálise de indeferidas, portanto, **nunca mostra indeferidas**. Falta um endpoint `GET /editais/{id}/inscricoes` (PRO_REITOR) com filtro de status.

---

## 🔵 4. Funcionalidades incompletas / lacunas
- Não há **endpoint para listar recursos** nem **tela de julgamento de recurso**: `judgeResource` em `api/avaliacoes.ts` nunca é usado.
- Não há tela para **designar comissão**, **cancelar edital** (`cancelEdital` sem uso), **retificar inscrição** (`retificarInscricao` sem uso), **notificações** (endpoint existe, UI não) nem **download de documentos** do candidato pelo avaliador.
- `GET /auth/sso/*` é apenas um stub que sempre autentica o estudante mock e ignora o `code`.
- Envio de e-mail das notificações: os campos `email_status` e `tentativas_email` existem, mas não há worker.
- `status_varredura` é sempre `"VALIDADO"`: não há antivírus nem quarentena (o model prevê `PENDENTE/QUARENTENA`).

---

## 🔵 5. Qualidade de código (backend)
- **Upload não é streaming de verdade**: `await upload_file.read()` carrega o arquivo inteiro em memória (`inscricao_service.py:150`), o que contradiz o README e o RNF-03. Reaproveitar `LocalStorageService.save` (que já faz chunks + validação) e calcular o SHA-256 incrementalmente.
- A validação de PDF/tamanho está **duplicada** em 3 lugares (storage, submeter, retificar). Consolidar no storage.
- O parsing de multipart `"".join(filter(str.isdigit, key))` está duplicado em dois routers e aceita chaves ambíguas (`doc1_2` vira `12`). Usar regex `^doc_(\d+)$` em um helper comum.
- `client_ip = request.client.host if ...` aparece repetido em todo endpoint. Criar uma dependência `get_client_ip` que respeite `X-Forwarded-For` (atrás do proxy do Render o IP gravado hoje é o do proxy, o que prejudica a auditoria).
- Status usados como strings soltas em todo o código. Criar `Enum`s (`EditalStatus`, `InscricaoStatus` etc.) e usá-los nos schemas (`Literal`) e models.
- Pydantic v2: trocar `class Config: from_attributes = True` por `model_config = ConfigDict(from_attributes=True)` (deprecation warning).
- `list_editais` declara retorno `-> (List[Edital], int)`, que não é uma anotação válida. Usar `tuple[list[Edital], int]`.
- `except Exception: pass` e `print()` no lifespan (`main.py:45-48`). Usar `logging` configurado por `LOG_LEVEL` (a variável existe mas não é usada).
- `health.py:22,34` expõe o texto da exceção do banco/storage publicamente. Logar internamente e retornar só `unhealthy`.
- `database.py:9`: `echo=True` em development polui os logs. Usar flag própria (`SQL_ECHO`).
- `pool_size=20, max_overflow=40` (60 conexões) excede o limite do PostgreSQL free do Render (~97 conexões totais, porém com plano de 256 MB a recomendação é bem menor). Parametrizar via env.
- `get_db` com `session.close()` redundante dentro de `async with`.
- Imports não usados em vários arquivos (`io`, `File`, `Form`, `Response`, `or_` etc.). Rodar `ruff`.
- `float(avaliacao.nota_merito) if avaliacao.nota_merito else None` (`avaliacao_service.py:129`) trata nota `0.00` como `None` na auditoria. Usar `is not None`.
- `datetime.now()` sem timezone no CSV (`report_service.py:25`), e o texto diz "Horário de Brasília" quando os horários estão em UTC. Converter com `zoneinfo.ZoneInfo("America/Sao_Paulo")`.

## 🔵 6. Qualidade de código (frontend)
- **Sem roteador**: a navegação é por `useState` (`App.tsx`). Não há URLs compartilháveis, o botão voltar não funciona e o F5 volta ao catálogo. Adotar `react-router-dom`.
- **Sem interceptor de resposta 401**: quando o token expira (120 min), `user_info` continua no `localStorage`, a UI parece logada e todas as chamadas falham. Adicionar um interceptor que faça logout ou redirecione.
- `AuthContext`: o papel ativo (`targetRole`) vem do **cliente**, não do servidor. É possível "logar como PRO_REITOR" com um e-mail de estudante e ver menus que retornarão 403. Usar `perfis` retornados pela API (ou `/auth/me`).
- Token JWT em `localStorage` fica vulnerável a XSS. Para produção, considerar cookie `HttpOnly` + `SameSite`.
- `client.ts:5-8`: URL do backend do Render **hard-coded**. Usar só `VITE_API_BASE_URL`.
- `alert()` usado em ~25 lugares. Trocar por um componente de toast.
- `downloadComprovante` não chama `URL.revokeObjectURL` (vazamento de memória).
- `tsconfig.json`: `"strict": false`. Ativar `strict` gradualmente. Há muitos `any` (`createEdital(data: any)`, `Promise<any>`).
- `package.json`: faltam os scripts `lint`, `typecheck` (`tsc --noEmit`) e `test`. Não há ESLint, Prettier nem Vitest.
- Valores numéricos (`Decimal`) chegam do backend como **string** em JSON (Pydantic v2), mas os tipos TS os declaram como `number`. Converter ou ajustar os tipos.
- Upload: não é preciso definir `'Content-Type': 'multipart/form-data'` manualmente (o axios/navegador define o boundary).

---

## 🔵 7. Infraestrutura / DevOps
- `backend/Dockerfile:23`: `--reload` no CMD da imagem, e `build-essential` permanece na imagem final. Usar multi-stage, usuário não-root e remover `--reload` (deixá-lo só no compose de dev).
- `frontend/Dockerfile`: roda `vite dev`. Para produção, fazer multi-stage com `npm ci && npm run build` servido por nginx.
- `docker-compose.yml`:
  - `version: '3.8'` está obsoleto (o Compose v2 emite aviso).
  - O backend monta o volume em `/data/documentos`, mas `.env.example` define `STORAGE_PATH=./data/documentos` (relativo a `/app`). **Os arquivos não vão para o volume nomeado.** Ajustar para `STORAGE_PATH=/data/documentos`.
  - O compose não executa `alembic upgrade head`. Adicionar ao comando de start ou criar um serviço `migrate`.
  - Postgres exposto em `5432` no host. Desnecessário fora de dev.
- `render.yaml`:
  - `STORAGE_PATH=./data/documentos` em um web service free usa **disco efêmero**: todos os PDFs somem a cada deploy/restart. Usar Render Disk (plano pago) ou S3/R2 (a interface `StorageService` já prevê isso).
  - O campo `env:` está depreciado; usar `runtime: python` / `runtime: static`.
  - `CORS_ORIGINS="*"` e `USE_MOCK_AUTH=true` (ver C3/C6).
- `requirements.txt`: só usa `>=`, sem *lock*, o que deixa builds não reprodutíveis. Fixar versões (`pip-compile` ou `uv lock`). Separar `pytest`/`locust` em `requirements-dev.txt`. Há duplicação com `pyproject.toml`; manter uma única fonte.
- `python-jose` está praticamente sem manutenção e tem CVEs históricas. Migrar para `PyJWT`. O `passlib` também está sem manutenção e emite avisos com `bcrypt>=4.1`. Considerar usar `bcrypt` direto ou `pwdlib`.
- **Sem CI**: criar um workflow GitHub Actions com `ruff`, `pytest`, `tsc --noEmit` e `npm run build`.
- **4 PDFs de especificação (versões v4, v5 e duas cópias)** estão versionados na raiz. Mover para `docs/` e manter só a versão vigente (as demais ficam no histórico do git).
- README: o passo `cd SistemasInfo` está errado (a pasta chama `quero_git`). A seção "Publicação no GitHub" ensina `git init` em um repo que já existe. Faltam a lista de usuários mock e o aviso de que a autenticação é simulada.

---

## 🔵 8. Testes
- A suíte atual testa **só schemas e funções puras**. Nenhum teste cobre endpoints, serviços com banco ou autorização. Por isso os bugs C1, C2 e C4 passaram despercebidos.
- `tests/load_test_locust.py` chama rotas **inexistentes** (`GET /editais/1/resultado-preliminar`, `POST /editais/1/inscricoes/rascunho`) e parâmetros que não existem (`page`, `size`). `locust` também não está nas dependências.
- `test_desempate_sorting_logic` testa um `sort` escrito **dentro do próprio teste**, não o código de produção.
- **Sugestão:**
  - Fixture com PostgreSQL de teste (testcontainers ou serviço no CI) + `httpx.AsyncClient(app=app)`.
  - Teste E2E do fluxo completo: criar edital → publicar → designar comissão → inscrever com PDF → encerrar → avaliar → publicar preliminar → recurso → julgar → homologar → baixar ata.
  - Testes de autorização (matriz perfil × endpoint).
  - Frontend: Vitest + Testing Library nas telas principais.

---

## 9. Plano de ação sugerido

| Prioridade | Itens | Esforço estimado |
|---|---|---|
| **Sprint 1: fazer funcionar** | C1, C2, C4, M1, M2, M6, M15, ajuste de `STORAGE_PATH` no compose | 1–2 dias |
| **Sprint 2: segurança** | C3, C5, C6, A1–A6, M14, 401 no frontend | 2–3 dias |
| **Sprint 3: regras de negócio** | A7–A12, M3–M5, M7–M9, M12, M13 | 3–4 dias |
| **Sprint 4: qualidade e entrega** | Testes de integração + CI, Enums, roteador no frontend, Dockerfiles de produção, storage persistente (S3), telas faltantes (recursos, comissão, notificações) | 1–2 semanas |
