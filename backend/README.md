# Backend

FastAPI + PostgreSQL/PostGIS + Redis.

## Quick start

```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Postgres + Redis (in repo root)
docker compose up db redis -d

alembic upgrade head
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs.

## Layout

```
app/
├── main.py            FastAPI app, middleware, router wiring
├── core/              Config, security, logging
├── db/                Engine, session, base
├── models/            SQLAlchemy ORM models
├── schemas/           Pydantic request/response models
├── repositories/      DB-access layer (one per aggregate)
├── services/          Business logic
└── api/v1/            HTTP + WebSocket routes
```

## Migrations

```bash
alembic revision --autogenerate -m "add foo"
alembic upgrade head
alembic downgrade -1
```

## Tests

```bash
pytest                       # all
pytest tests/test_auth.py    # one file
pytest -k spot               # by keyword
pytest --cov=app             # with coverage
```
