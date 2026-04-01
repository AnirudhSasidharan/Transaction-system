# Real-Time Transaction System

A payments and trading simulator backend built to demonstrate:

- **Async transaction processing** — API responds instantly, processing happens in the background
- **Real-time WebSocket updates** — browser receives live status changes, no polling
- **Double-spend prevention** — PostgreSQL row locking ensures funds can't be spent twice
- **Event-driven architecture** — `API → Queue → Worker → DB → WebSocket`

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI | Async, fast, auto-generates docs |
| Queue + Pub/Sub | Redis | In-memory, microsecond speed |
| Database | PostgreSQL | ACID transactions, row-level locking |
| ORM | SQLAlchemy (async) | Python instead of raw SQL |
| Migrations | Alembic | Version control for the database schema |
| Containerization | Docker Compose | One command to run everything |

---

## Project Structure

```
backend/
├── app/
│   ├── api/            # HTTP routes (wallets, transactions, websocket)
│   ├── core/           # Config, DB connection, Redis client
│   ├── models/         # Database tables (SQLAlchemy)
│   ├── schemas/        # API input/output shapes (Pydantic)
│   ├── services/       # Business logic
│   ├── workers/        # Background queue processor
│   └── main.py         # App entry point
├── alembic/            # Database migrations
├── tests/              # Automated tests
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/transaction-system.git
cd transaction-system

# 2. Set up environment variables
cp .env.example .env

# 3. Start all services (PostgreSQL + Redis + API)
docker compose up --build

# 4. Apply database migrations
docker compose exec api alembic upgrade head

# 5. Open interactive API docs
open http://localhost:8000/docs
```

---

## Running Locally (without Docker)

```bash
# Prerequisites: Python 3.12+, PostgreSQL, Redis running locally

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit DATABASE_URL and REDIS_URL

alembic upgrade head            # create tables
uvicorn app.main:app --reload   # start the server
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/wallets/` | Create a wallet |
| `GET` | `/api/v1/wallets/{user_id}` | Get wallet and balance |
| `POST` | `/api/v1/wallets/{user_id}/topup` | Add funds (demo) |
| `POST` | `/api/v1/transactions/` | Create a transaction — returns `pending` instantly |
| `GET` | `/api/v1/transactions/{id}` | Get transaction status |
| `GET` | `/api/v1/transactions/history/{user_id}` | Paginated history |
| `WS` | `/api/v1/ws/{user_id}` | Real-time updates via WebSocket |

---

## How a Transaction Works

```
Client      API            Redis         Worker         DB
  │           │               │              │             │
  ├─POST /tx─▶│               │              │             │
  │           ├─INSERT PENDING───────────────────────────▶│
  │           ├─LPUSH tx_id──▶│              │             │
  │◀─201 ─────│               │              │             │
  │           │               │◀─BRPOP───────┤             │
  │           │               │              ├─UPDATE PROC▶│
  │           │               │              ├─DEDUCT BAL─▶│
  │           │               │              ├─UPDATE SUCC▶│
  │◀─WS update────────────────────────────────────────────│
```

---

