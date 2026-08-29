<div align="center">

# 🎟️ Ticket Plus — Event Tickets E-Commerce API

<p align="center">
  <a href="./README.md">🌐 English</a> │
  <a href="./README.pt-br.md">🇧🇷 Português</a>
</p>

---

**A modular REST API for event ticket sales, built with FastAPI and MySQL.**
Covers the full lifecycle from event creation and ticket type management to checkout, payment processing and PDF ticket generation.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![MySQL 8.0+](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

</div>


## 📖 About

**Ticket Plus** is a full-featured e-commerce backend for buying and selling event tickets. It was built primarily as a personal learning project to consolidate practical knowledge of modular software architecture in backend development, evolving from simple single-file scripts to a clean, layered MVC application (in this case).

Ticket Plus is an educational project, not a commercial product. That said, I plan to refine and update it whenever time permits. The codebase was intentionally built to be modular, readable, and easy to extend.

**Feel free to fork it, modify it, rebrand it, or adapt both the frontend and backend for your own needs!** Whether you want to rename it, use it as a learning reference, or turn it into the foundation for something bigger, you have full freedom under the MIT License.

> **_Note: This application was developed specifically for the Brazilian market, featuring Brazilian cities and a Portuguese user interface. However, the codebase and documentation are available in English for international review and reusability._**

---

## ✨ Features

- 🔐 **Authentication** — JWT-based session management with Argon2 password hashing and rate limiting
- 🎭 **Event Management** — Full CRUD for events (with image uploads, location validation, capacity control)
- 🎫 **Ticket Types** — Create and manage ticket categories (`standard`, `vip`, `early_bird`, `group`) with per-cent pricing
- 🛒 **Order & Checkout** — Idempotent order creation with Stripe payment intent integration
- 🪝 **Stripe Webhooks** — Atomic ticket generation on confirmed payments (no partial writes)
- 📄 **PDF Ticket Generation** — ReportLab + QR Code for each individual ticket holder
- 🔍 **Audit Logging** — Full action history (create, update, delete, login) with IP and User-Agent tracking
- ✅ **Complete Test Suite** — 53 integration tests with a live MySQL database, automated via GitHub Actions

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) | HTTP routing, dependency injection, async support |
| **Language** | Python 3.12+ | Core runtime |
| **Database** | MySQL 8.0+ | Primary data store |
| **Async Driver** | `aiomysql` | Async MySQL connection for SQLAlchemy |
| **ORM / Queries** | SQLAlchemy (Core, raw `text()`) | Database engine and connection management |
| **Validation** | Pydantic v2 | Schema validation with pre-validators for form data |
| **Auth** | PyJWT + Passlib / Argon2 | Token generation and password hashing |
| **Payments** | Stripe SDK | Payment intent creation and webhook verification |
| **PDF** | ReportLab + qrcode + Pillow | Ticket PDF generation |
| **Templates** | Jinja2 | Server-side HTML rendering |
| **Rate Limiting** | SlowAPI | Endpoint protection against abuse |
| **Testing** | pytest + pytest-asyncio | Integration test suite against a live DB |
| **CI/CD** | GitHub Actions | Automated test pipeline on push/PR |
| **Config** | python-dotenv + pydantic-settings | Environment variable management |

---

## 📁 Project Structure

```
tix-plus/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI pipeline
├── app/
│   ├── middleware/
│   │   ├── csrf.py              # CSRF token middleware
│   │   └── rate_limiter.py      # SlowAPI rate limiting setup
│   ├── routes/
│   │   ├── admin.py             # Admin panel routes
│   │   ├── auth.py              # Register, login, logout
│   │   ├── events.py            # Event CRUD + ticket types
│   │   ├── orders.py            # Checkout, webhook, order management
│   │   ├── tickets.py           # Ticket holder info, PDF download
│   │   └── users.py             # User profile management
│   ├── schemas/
│   │   └── schemas.py           # All Pydantic models and validators
│   ├── services/
│   │   ├── audit_service.py     # Audit log operations
│   │   ├── auth_service.py      # User creation, JWT, authentication
│   │   ├── event_service.py     # Event and ticket type business logic
│   │   ├── image_service.py     # Banner upload/delete
│   │   ├── order_service.py     # Order creation, payment, webhook handler
│   │   ├── ticket_service.py    # Ticket creation, PDF generation
│   │   └── user_service.py      # User profile updates
│   ├── templates/               # Jinja2 HTML templates
│   ├── config.py                # Settings (pydantic-settings) + templates path
│   ├── database.py              # Async SQLAlchemy engine + session factory
│   └── main.py                  # FastAPI app entry point, router inclusion
├── tests/
│   ├── conftest.py              # Shared fixtures, DB cleanup, mock setup
│   ├── test_auth_service.py
│   ├── test_event_service.py
│   ├── test_order_service.py
│   ├── test_ticket_service.py
│   └── test_user_service.py
├── schema.sql                   # Raw SQL schema (all tables)
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development & test dependencies
├── Dockerfile                   # Container image definition
├── compose.yaml                 # Docker Compose configuration
├── pytest.ini                   # pytest configuration
├── .dockerignore                # Docker build exclusions
├── .env.example                 # Environment variable template
├── READ.pt-br.md
└── README.md
```

---

## 🗄️ Database Schema

The following tables form the core data model. All monetary values are stored in **integer cents** (e.g., `10000` = R$ 100,00) for Stripe compatibility.

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

## ⚙️ Setup & Installation

### Prerequisites

- **Python 3.12+**
- **MySQL 8.0+** (local or via Docker)
- **Docker & Docker Compose** (optional but recommended)

### Step-by-step

#### Option 1: Local Setup (without Docker)

1. **Clone the repository**

```bash
git clone https://github.com/Yahg0h/ticket-plus.git
cd ticket-plus
```

2. **Create and activate the virtual environment**

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

> **MySQL 8+ Auth Note:** If you get a `cryptography` error when connecting, run:
> ```bash
> pip install cryptography
> ```

4. **Configure environment variables**

Copy `.env.example` to `.env` and fill in your values:

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

5. **Create the database and apply the schema**

```bash
mysql -u root -p -e "CREATE DATABASE tixplus_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p tixplus_db < schema.sql
```

6. **Run the application**

```bash
uvicorn app.main:app --reload
```

API available at `http://localhost:8000` · Interactive docs at `http://localhost:8000/docs`.

7. **Run the test suite**

```bash
pytest -v
```

Expected output with a live database:

```
======================= 53 passed, 1 warning in 35.45s ========================
```

#### Option 2: Docker Setup (Recommended)

Running with Docker Compose is the easiest way to spin up the entire application stack, including a fully configured MySQL 8.0 instance, without installing dependencies locally.

1. **Clone the repository**:
```bash
   git clone https://github.com/yahg0h/ticket-plus.git
   cd ticket-plus
```

2. **Configure environment variables**:
Copy `.env.example` to `.env` and fill in your values:

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

3. **Build and start the containers**:
   ```bash
   docker compose up --build -d
   ```

   >Note: The MySQL container includes a built-in healthcheck. The FastAPI app container will wait for the database to become healthy before starting.

4. **Access the application**:
   - Web App: http://localhost:8000
   - Interactive API Docs (Swagger): http://localhost:8000/docs

---

## 🔄 Continuous Integration (CI/CD)

The GitHub Actions pipeline (`.github/workflows/ci.yml`) runs automatically on every push to `main`, `develop` and `feature/**` branches, and on all pull requests targeting `main` or `develop`.

**Pipeline steps:**

1. ✅ **Checkout code** — `actions/checkout@v4`
2. 🐍 **Setup Python 3.14** — with pip caching enabled
3. 📦 **Install dependencies** — `requirements.txt` + `pytest`, `mypy`, `ruff`, `aiomysql`, `cryptography`
4. 🐬 **Provision MySQL 8.0 service** — health-checked Docker container on port `3306`
5. ⏳ **Wait for MySQL** — async connection probe with 30 retries
6. 🏗️ **Create test database** — `ticket_plus_test` provisioned via pymysql
7. 🧪 **Run pytest** — full suite with coverage report (`--cov=app --cov-report=xml`)
8. 📊 **Upload coverage** — to Codecov (non-blocking)
9. 🔍 **Lint** — `ruff check` (non-blocking, informational)
10. 🔎 **Type check** — `mypy` (non-blocking, informational)

All environment variables (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `JWT_SECRET`, `STRIPE_*`) are injected directly into the test step via the workflow `env:` block, keeping secrets out of the repo.

---

## 🛣️ Routes

### Auth (`/auth`)

| Method | Route | Auth Required | Description |
|--------|-------|:---:|-------------|
| `GET` | `/auth/register` | ❌ | Render registration page |
| `POST` | `/auth/register` | ❌ | Create a new user account |
| `GET` | `/auth/login` | ❌ | Render login page |
| `POST` | `/auth/login` | ❌ | Authenticate and issue JWT cookie |
| `POST` | `/auth/logout` | ✅ | Invalidate session |

### Events (`/events`)

| Method | Route | Auth Required | Description |
|--------|-------|:---:|-------------|
| `GET` | `/events` | ❌ | Public event listing with filters and pagination |
| `GET` | `/events/{event_id}` | ❌ | Public event detail page |
| `GET` | `/events/new` | ✅ | Render event creation form |
| `POST` | `/events/new` | ✅ | Create a new event |
| `GET` | `/events/{event_id}/edit` | ✅ | Render event edit form |
| `POST` | `/events/{event_id}/edit` | ✅ | Update event details |
| `POST` | `/events/{event_id}/delete` | ✅ | Delete event (organizer only) |
| `GET` | `/events/my-events` | ✅ | List organizer's own events |

### Ticket Types (`/events/{id}/ticket-types`)

| Method | Route | Auth Required | Description |
|--------|-------|:---:|-------------|
| `POST` | `/events/{id}/ticket-types` | ✅ | Add a ticket type to an event |
| `POST` | `/events/{id}/ticket-types/{tt_id}/edit` | ✅ | Update ticket type price/quantity |
| `POST` | `/events/{id}/ticket-types/{tt_id}/delete` | ✅ | Delete ticket type |

### Orders (`/orders`)

| Method | Route | Auth Required | Description |
|--------|-------|:---:|-------------|
| `GET` | `/orders/checkout/{ticket_type_id}` | ✅ | Render checkout page |
| `POST` | `/orders/checkout/{ticket_type_id}` | ✅ | Create order and Stripe payment intent |
| `POST` | `/orders/webhook` | ❌ | Stripe webhook: confirm/fail payment |
| `GET` | `/orders/my-orders` | ✅ | List buyer''s orders |
| `POST` | `/orders/{order_id}/cancel` | ✅ | Cancel a pending order |

### Tickets (`/tickets`)

| Method | Route | Auth Required | Description |
|--------|-------|:---:|-------------|
| `GET` | `/tickets/my-tickets` | ✅ | List buyer''s tickets |
| `GET` | `/tickets/{order_id}/fill` | ✅ | Render ticket holder info form |
| `POST` | `/tickets/{order_id}/fill` | ✅ | Submit ticket holder names and CPFs |
| `GET` | `/tickets/{ticket_id}/pdf` | ✅ | Download ticket as PDF |

---

## 🏛️ Architecture & Engineering Insights

### Modular Architecture

The project enforces a strict separation of concerns across three layers:

```
HTTP Request
    │
    ▼
┌─────────────┐   Input validation    ┌──────────────┐
│   Routes    │ ──────────────────▶  │   Schemas    │
│  (FastAPI)  │ ◀── 422 on invalid ─ │  (Pydantic)  │
└─────────────┘                       └──────────────┘
    │
    │  Calls service functions
    ▼
┌─────────────┐   Business rules      ┌──────────────┐
│  Services   │ ─── ValueError ─────▶ │   Database   │
│  (Python)   │ ◀── dicts/scalars ── │  (MySQL via  │
└─────────────┘                       │  SQLAlchemy) │
    │                                  └──────────────┘
    │  Returns data / raises HTTPException
    ▼
HTTP Response
```

- **Routes** handle HTTP concerns only (status codes, cookies, redirects) and translate `ValueError` from services into clean `HTTPException` responses.
- **Services** contain all business logic and database operations. They are framework-agnostic and independently testable.
- **Schemas** are the single source of truth for data shapes, with pre-validators for robust form parsing.



## 🔧 Troubleshooting

### `RuntimeError: 'cryptography' package is required for sha256_password or caching_sha2_password auth methods`

MySQL 8.0 uses `caching_sha2_password` by default. The `aiomysql` driver requires the `cryptography` package for this handshake.

```bash
pip install cryptography
```



### `OperationalError: (2003) Can''t connect to MySQL server on ''db''`

The `.env` file has `DB_HOST=db` (the Docker Compose service name). When running locally without Docker, change it to `DB_HOST=localhost`.



### Duplicate fixture warning from conftest.py

`conftest.py` had two fixtures with the same name defined at different points — a copy-paste artifact. pytest uses the last definition but emits a `PytestWarning`. Remove the first (duplicate) block of both `mock_external_services` and `clean_db`.

---

### Tests fail with `IntegrityError` after an interrupted run

If a test run is killed before teardown, the `TRUNCATE TABLE` in `clean_db` may not execute. Reset manually:

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



## 📄 License

This project is licensed under the [MIT License](./LICENSE).



## 👤 Author

Made by **Yahg0h**
- GitHub: [@yahg0h](https://github.com/yahg0h)


