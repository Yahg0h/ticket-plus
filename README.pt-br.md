<div align="center">

# 🎟️ Ticket Plus — API de E-Commerce de Ingressos para Eventos

<p align="center">
  <a href="./README.md">🌐 English</a> │
  <a href="./README.pt-br.md">🇧🇷 Português</a>
</p>

---

**Uma API REST modular para venda de ingressos de eventos, construída com FastAPI e MySQL.**
Abrange todo o ciclo, desde a criação de eventos e gerenciamento de tipos de ingresso até o checkout, processamento de pagamentos e geração de ingressos em PDF.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![MySQL 8.0+](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

</div>


## 📖 Sobre

**Ticket Plus** é um backend completo de e-commerce para compra e venda de ingressos de eventos. Foi desenvolvido principalmente como um projeto pessoal de aprendizado, com o objetivo de consolidar conhecimentos práticos de arquitetura modular de software no desenvolvimento backend, evoluindo de scripts simples em um único arquivo para uma aplicação MVC limpa e em camadas (neste caso).

O Ticket Plus é um projeto educacional, não um produto comercial. Ainda assim, pretendo aprimorá-lo e atualizá-lo sempre que possível. A base de código foi desenvolvida intencionalmente para ser modular, legível e fácil de expandir.

> **Sinta-se à vontade para fazer um fork, modificá-lo, mudar sua marca ou adaptar tanto o frontend quanto o backend às suas necessidades!** Seja para renomeá-lo, usá-lo como referência de aprendizado ou transformá-lo na base de algo maior, você tem total liberdade sob a Licença MIT.

---

## ✨ Funcionalidades

- 🔐 **Autenticação** — Gerenciamento de sessões baseado em JWT, com hash de senhas usando Argon2 e limitação de requisições
- 🎭 **Gerenciamento de Eventos** — CRUD completo de eventos (com upload de imagens, validação de localização e controle de capacidade)
- 🎫 **Tipos de Ingresso** — Criação e gerenciamento de categorias de ingresso (`standard`, `vip`, `early_bird`, `group`) com preços armazenados em centavos
- 🛒 **Pedidos e Checkout** — Criação idempotente de pedidos com integração aos Payment Intents da Stripe
- 🪝 **Webhooks da Stripe** — Geração atômica de ingressos após pagamentos confirmados (sem gravações parciais)
- 📄 **Geração de Ingressos em PDF** — ReportLab + QR Code para cada titular de ingresso
- 🔍 **Logs de Auditoria** — Histórico completo de ações (criação, atualização, exclusão e login), com rastreamento de IP e User-Agent
- ✅ **Suíte de Testes Completa** — 53 testes de integração com um banco MySQL ativo, automatizados pelo GitHub Actions

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Finalidade |
|---|---|---|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) | Roteamento HTTP, injeção de dependências e suporte assíncrono |
| **Linguagem** | Python 3.12+ | Runtime principal |
| **Banco de dados** | MySQL 8.0+ | Armazenamento principal de dados |
| **Driver assíncrono** | `aiomysql` | Conexão assíncrona com MySQL para SQLAlchemy |
| **ORM / Queries** | SQLAlchemy (Core, `text()` bruto) | Gerenciamento do engine e das conexões com o banco |
| **Validação** | Pydantic v2 | Validação de schemas com pré-validadores para dados de formulários |
| **Autenticação** | PyJWT + Passlib / Argon2 | Geração de tokens e hash de senhas |
| **Pagamentos** | Stripe SDK | Criação de Payment Intents e verificação de webhooks |
| **PDF** | ReportLab + qrcode + Pillow | Geração de ingressos em PDF |
| **Templates** | Jinja2 | Renderização de HTML no servidor |
| **Rate Limiting** | SlowAPI | Proteção dos endpoints contra abuso |
| **Testes** | pytest + pytest-asyncio | Suíte de testes de integração contra um banco ativo |
| **CI/CD** | GitHub Actions | Pipeline automatizado de testes em push/PR |
| **Configuração** | python-dotenv + pydantic-settings | Gerenciamento de variáveis de ambiente |

---

## 📁 Estrutura do Projeto

```
tix-plus/
├── .github/
│   └── workflows/
│       └── ci.yml               # Pipeline de CI do GitHub Actions
├── app/
│   ├── middleware/
│   │   ├── csrf.py              # Middleware de token CSRF
│   │   └── rate_limiter.py      # Configuração do rate limiting com SlowAPI
│   ├── routes/
│   │   ├── admin.py             # Rotas do painel administrativo
│   │   ├── auth.py              # Cadastro, login e logout
│   │   ├── events.py            # CRUD de eventos + tipos de ingresso
│   │   ├── orders.py            # Checkout, webhook e gerenciamento de pedidos
│   │   ├── tickets.py           # Dados do titular e download do PDF
│   │   └── users.py             # Gerenciamento do perfil do usuário
│   ├── schemas/
│   │   └── schemas.py           # Todos os modelos e validadores Pydantic
│   ├── services/
│   │   ├── audit_service.py     # Operações de logs de auditoria
│   │   ├── auth_service.py      # Criação de usuários, JWT e autenticação
│   │   ├── event_service.py     # Lógica de negócio de eventos e tipos de ingresso
│   │   ├── image_service.py     # Upload/exclusão de banners
│   │   ├── order_service.py     # Criação de pedidos, pagamento e handler de webhook
│   │   ├── ticket_service.py    # Criação de ingressos e geração de PDF
│   │   └── user_service.py      # Atualizações do perfil do usuário
│   ├── templates/               # Templates HTML Jinja2
│   ├── config.py                # Configurações (pydantic-settings) + caminho dos templates
│   ├── database.py              # Engine assíncrono SQLAlchemy + fábrica de sessões
│   └── main.py                  # Ponto de entrada da aplicação FastAPI e inclusão de routers
├── tests/
│   ├── conftest.py              # Fixtures compartilhadas, limpeza do banco e mocks
│   ├── test_auth_service.py
│   ├── test_event_service.py
│   ├── test_order_service.py
│   ├── test_ticket_service.py
│   └── test_user_service.py
├── schema.sql                   # Schema SQL bruto (todas as tabelas)
├── requirements.txt             # Dependências de produção
├── requirements-dev.txt         # Dependências de desenvolvimento e testes
├── Dockerfile                   # Definição da imagem do container
├── compose.yaml                 # Configuração do Docker Compose
├── pytest.ini                   # Configuração do pytest
├── .dockerignore                # Exclusões do build do Docker
├── .env.example                 # Template de variáveis de ambiente
├── READ.pt-br.md
└── README.md
```

---

## 🗄️ Schema do Banco de Dados

As tabelas a seguir formam o modelo de dados principal. Todos os valores monetários são armazenados em **centavos inteiros** (por exemplo, `10000` = R$ 100,00) para compatibilidade com a Stripe.

```sql
-- Users (buyers and organizers)
CREATE TABLE users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(255) UNIQUE NULL,
    phone_number  VARCHAR(20) UNIQUE NULL,
    password_hash VARCHAR(255) NOT NULL,
    cpf           VARCHAR(14) UNIQUE NOT NULL,
    state         VARCHAR(255) NOT NULL,
    city          VARCHAR(255) NOT NULL,
    is_admin      BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_user_contact CHECK (email IS NOT NULL OR phone_number IS NOT NULL)
);

-- Events
CREATE TABLE events (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    organizer_id      INT NOT NULL,
    title             VARCHAR(255) NOT NULL,
    description       TEXT NULL,
    banner_url        VARCHAR(255) NULL,
    category          ENUM('entertainment','corporate','academic','social','sports','marketing','workshop','other') NOT NULL,
    state             VARCHAR(255) NOT NULL,
    city              VARCHAR(255) NOT NULL,
    address           VARCHAR(255) NOT NULL,
    total_capacity    INT NOT NULL,
    available_tickets INT NOT NULL,
    start_date        DATETIME NOT NULL,
    end_date          DATETIME NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (organizer_id) REFERENCES users(id) ON DELETE RESTRICT
);

-- Ticket Types (standard, vip, early_bird, group)
CREATE TABLE ticket_types (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    event_id           INT NOT NULL,
    type               ENUM('standard','vip','early_bird','group') NOT NULL,
    price              INT NOT NULL,     -- Value in cents: 10000 = R$ 100,00
    quantity_available INT NOT NULL,
    quantity_sold      INT DEFAULT 0,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

-- Orders
CREATE TABLE orders (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    buyer_id          INT NOT NULL,
    event_id          INT NOT NULL,
    ticket_type_id    INT NOT NULL,
    quantity          INT NOT NULL DEFAULT 1,
    total_amount      INT NOT NULL,
    payment_status    ENUM('pending','paid','failed','refunded') DEFAULT 'pending',
    stripe_payment_id VARCHAR(255) NULL,
    idempotency_key   VARCHAR(255) UNIQUE NOT NULL,
    order_status      ENUM('pending','confirmed','cancelled','completed') DEFAULT 'pending',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at      DATETIME NULL,
    FOREIGN KEY (buyer_id)  REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (event_id)  REFERENCES events(id) ON DELETE RESTRICT
);

-- Individual Tickets (one row per person)
CREATE TABLE tickets (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    order_id       INT NOT NULL,
    ticket_type_id INT NOT NULL,
    holder_name    VARCHAR(255) NOT NULL,
    holder_cpf     VARCHAR(14) NOT NULL,
    price_paid     INT NOT NULL,
    status         ENUM('valid','used','cancelled') DEFAULT 'valid',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id)       REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (ticket_type_id) REFERENCES ticket_types(id) ON DELETE RESTRICT
);

-- Audit Logs
CREATE TABLE audit_logs (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NULL,
    action         VARCHAR(50) NOT NULL,
    auditable_type VARCHAR(50) NOT NULL,
    auditable_id   INT NOT NULL,
    old_values     JSON NULL,
    new_values     JSON NULL,
    ip_address     VARCHAR(45) NULL,
    user_agent     VARCHAR(255) NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

---

## ⚙️ Configuração e Instalação

### Pré-requisitos

- **Python 3.12+**
- **MySQL 8.0+** (localmente ou via Docker)
- **Docker e Docker Compose** (opcional, mas recomendado)

### Passo a passo

#### Opção 1: Configuração local (sem Docker)

1. **Clone o repositório**

```bash
git clone https://github.com/Yahg0h/ticket-plus.git
cd ticket-plus
```

2. **Crie e ative o ambiente virtual**

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

3. **Instale as dependências**

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

> **Nota de autenticação do MySQL 8+:** Se você receber um erro relacionado ao `cryptography` ao conectar, execute:
> ```bash
> pip install cryptography
> ```

4. **Configure as variáveis de ambiente**

Copie `.env.example` para `.env` e preencha os seus valores:

```bash
cp .env.example .env
```

```env
# Database
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=tixplus_db

# Security
JWT_SECRET=your_super_secret_key_here

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

5. **Crie o banco de dados e aplique o schema**

```bash
mysql -u root -p -e "CREATE DATABASE tixplus_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p tixplus_db < schema.sql
```

6. **Execute a aplicação**

```bash
uvicorn app.main:app --reload
```

API disponível em `http://localhost:8000` · Documentação interativa em `http://localhost:8000/docs`.

7. **Execute a suíte de testes**

```bash
pytest -v
```

Saída esperada com um banco de dados ativo:

```
======================= 53 passed, 1 warning in 35.45s ========================
```

#### Opção 2: Configuração com Docker (Recomendada)

Executar com Docker Compose é a maneira mais fácil de iniciar toda a stack da aplicação, incluindo uma instância do MySQL 8.0 totalmente configurada, sem precisar instalar as dependências localmente.

1. **Clone o repositório**:
```bash
   git clone https://github.com/yahg0h/ticket-plus.git
   cd ticket-plus
```

2. **Configure as variáveis de ambiente**:
Copie `.env.example` para `.env` e preencha os seus valores:

```bash
cp .env.example .env
```

```env
# Database
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    DB_HOST=db
    DB_PORT=3306
    DB_NAME=tixplus_db

    # Security
    JWT_SECRET=your_super_secret_key_here

    # Stripe
    STRIPE_SECRET_KEY=sk_test_...
    STRIPE_PUBLISHABLE_KEY=pk_test_...
    STRIPE_WEBHOOK_SECRET=whsec_...
```

3. **Construa e inicie os containers**:
   ```bash
   docker compose up --build -d
   ```

   >Nota: O container do MySQL inclui um healthcheck integrado. O container da aplicação FastAPI aguardará o banco de dados ficar saudável antes de iniciar.

4. **Acesse a aplicação**:
   - Aplicação Web: http://localhost:8000
   - Documentação interativa da API (Swagger): http://localhost:8000/docs

---

## 🔄 Integração Contínua (CI/CD)

O pipeline do GitHub Actions (`.github/workflows/ci.yml`) é executado automaticamente a cada push nas branches `main`, `develop` e `feature/**`, e em todos os pull requests direcionados para `main` ou `develop`.

**Etapas do pipeline:**

1. ✅ **Checkout do código** — `actions/checkout@v4`
2. 🐍 **Configuração do Python 3.14** — com cache do pip habilitado
3. 📦 **Instalação das dependências** — `requirements.txt` + `pytest`, `mypy`, `ruff`, `aiomysql`, `cryptography`
4. 🐬 **Provisionamento do serviço MySQL 8.0** — container Docker com healthcheck na porta `3306`
5. ⏳ **Aguarda o MySQL** — teste assíncrono de conexão com 30 tentativas
6. 🏗️ **Criação do banco de testes** — `ticket_plus_test` provisionado via pymysql
7. 🧪 **Execução do pytest** — suíte completa com relatório de cobertura (`--cov=app --cov-report=xml`)
8. 📊 **Upload da cobertura** — para o Codecov (não bloqueante)
9. 🔍 **Lint** — `ruff check` (não bloqueante, informativo)
10. 🔎 **Verificação de tipos** — `mypy` (não bloqueante, informativo)

Todas as variáveis de ambiente (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `JWT_SECRET`, `STRIPE_*`) são injetadas diretamente na etapa de testes por meio do bloco `env:` do workflow, mantendo os segredos fora do repositório.

---

## 🛣️ Rotas

### Autenticação (`/auth`)

| Método | Rota | Autenticação necessária | Descrição |
|--------|-------|:---:|-------------|
| `GET` | `/auth/register` | ❌ | Renderiza a página de cadastro |
| `POST` | `/auth/register` | ❌ | Cria uma nova conta de usuário |
| `GET` | `/auth/login` | ❌ | Renderiza a página de login |
| `POST` | `/auth/login` | ❌ | Autentica e emite um cookie JWT |
| `POST` | `/auth/logout` | ✅ | Invalida a sessão |

### Eventos (`/events`)

| Método | Rota | Autenticação necessária | Descrição |
|--------|-------|:---:|-------------|
| `GET` | `/events` | ❌ | Lista pública de eventos com filtros e paginação |
| `GET` | `/events/{event_id}` | ❌ | Página pública de detalhes do evento |
| `GET` | `/events/new` | ✅ | Renderiza o formulário de criação de evento |
| `POST` | `/events/new` | ✅ | Cria um novo evento |
| `GET` | `/events/{event_id}/edit` | ✅ | Renderiza o formulário de edição do evento |
| `POST` | `/events/{event_id}/edit` | ✅ | Atualiza os dados do evento |
| `POST` | `/events/{event_id}/delete` | ✅ | Exclui o evento (somente o organizador) |
| `GET` | `/events/my-events` | ✅ | Lista os próprios eventos do organizador |

### Tipos de Ingresso (`/events/{id}/ticket-types`)

| Método | Rota | Autenticação necessária | Descrição |
|--------|-------|:---:|-------------|
| `POST` | `/events/{id}/ticket-types` | ✅ | Adiciona um tipo de ingresso a um evento |
| `POST` | `/events/{id}/ticket-types/{tt_id}/edit` | ✅ | Atualiza o preço/quantidade do tipo de ingresso |
| `POST` | `/events/{id}/ticket-types/{tt_id}/delete` | ✅ | Exclui o tipo de ingresso |

### Pedidos (`/orders`)

| Método | Rota | Autenticação necessária | Descrição |
|--------|-------|:---:|-------------|
| `GET` | `/orders/checkout/{ticket_type_id}` | ✅ | Renderiza a página de checkout |
| `POST` | `/orders/checkout/{ticket_type_id}` | ✅ | Cria o pedido e o Payment Intent da Stripe |
| `POST` | `/orders/webhook` | ❌ | Webhook da Stripe: confirma/falha o pagamento |
| `GET` | `/orders/my-orders` | ✅ | Lista os pedidos do comprador |
| `POST` | `/orders/{order_id}/cancel` | ✅ | Cancela um pedido pendente |

### Ingressos (`/tickets`)

| Método | Rota | Autenticação necessária | Descrição |
|--------|-------|:---:|-------------|
| `GET` | `/tickets/my-tickets` | ✅ | Lista os ingressos do comprador |
| `GET` | `/tickets/{order_id}/fill` | ✅ | Renderiza o formulário de dados dos titulares |
| `POST` | `/tickets/{order_id}/fill` | ✅ | Envia os nomes e CPFs dos titulares dos ingressos |
| `GET` | `/tickets/{ticket_id}/pdf` | ✅ | Baixa o ingresso em PDF |

---

## 🏛️ Arquitetura e Decisões de Engenharia

### Arquitetura Modular

O projeto aplica uma separação rigorosa de responsabilidades entre três camadas:

```
HTTP Request
    │
    ▼
┌─────────────┐   Input validation    ┌──────────────┐
│   Routes    │ ──────────────────▶  │   Schemas    │
│  (FastAPI)  │ ◀── 422 on invalid ─ │  (Pydantic)  │
└─────────────┘                       └──────────────┘
    │
    │  Chama funções dos services
    ▼
┌─────────────┐   Business rules      ┌──────────────┐
│  Services   │ ─── ValueError ─────▶ │   Database   │
│  (Python)   │ ◀── dicts/scalars ── │  (MySQL via  │
└─────────────┘                       │  SQLAlchemy) │
    │                                  └──────────────┘
    │  Retorna dados / lança HTTPException
    ▼
HTTP Response
```

- **Routes** lidam apenas com questões HTTP (status codes, cookies e redirects) e traduzem `ValueError` dos services em respostas `HTTPException` adequadas.
- **Services** contêm toda a lógica de negócio e as operações de banco de dados. Eles são independentes de framework e podem ser testados isoladamente.
- **Schemas** são a fonte única de verdade para os formatos dos dados, com pré-validadores para um parsing robusto de formulários.



## 🔧 Solução de Problemas

### `RuntimeError: 'cryptography' package is required for sha256_password or caching_sha2_password auth methods`

O MySQL 8.0 usa `caching_sha2_password` por padrão. O driver `aiomysql` requer o pacote `cryptography` para esse handshake.

```bash
pip install cryptography
```



### `OperationalError: (2003) Can''t connect to MySQL server on ''db''`

O arquivo `.env` está com `DB_HOST=db` (o nome do serviço no Docker Compose). Ao executar localmente sem Docker, altere para `DB_HOST=localhost`.



### Aviso de fixture duplicada no conftest.py

O `conftest.py` tinha duas fixtures com o mesmo nome definidas em pontos diferentes — um artefato de copiar e colar. O pytest usa a última definição, mas emite um `PytestWarning`. Remova o primeiro bloco (duplicado) de `mock_external_services` e `clean_db`.

---

### Os testes falham com `IntegrityError` após uma execução interrompida

Se a execução dos testes for interrompida antes do teardown, o `TRUNCATE TABLE` em `clean_db` pode não ser executado. Faça o reset manualmente:

```sql
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE audit_logs;
TRUNCATE TABLE tickets;
TRUNCATE TABLE orders;
TRUNCATE TABLE ticket_types;
TRUNCATE TABLE events;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;
```



## 📄 Licença

Este projeto é licenciado sob a [Licença MIT](./LICENSE).



## 👤 Autor

Desenvolvido por **Yahg0h**
- GitHub: [@yahg0h](https://github.com/yahg0h)


