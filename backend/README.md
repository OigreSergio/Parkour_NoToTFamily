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
├── legal/             The risk notices, versioned, as code
├── data/              Static domain data (the vault catalogue)
├── models/            SQLAlchemy ORM models
├── schemas/           Pydantic request/response models
├── repositories/      DB-access layer (one per aggregate)
├── services/          Business logic
└── api/v1/            HTTP + WebSocket routes
```

## Signing in

There is no password in the main flow. `POST /api/v1/auth/email/request-code`
mails a six-digit code from the no-reply sender;
`POST /api/v1/auth/email/verify-code` checks it and either signs the member in
or creates the account, its profile row and the record of the risk notice they
accepted. What the app asks next is driven by `GET /api/v1/onboarding/state`.

With `MAIL_BACKEND=console` (the default outside production) the code is
printed to the log *and* returned as `debug_code`, so the whole flow works
without a mail server.

`POST /api/v1/auth/guest` is the other way in: no email, no chosen name, and a
`guest_key` returned once that is the only way back to the account. From there
the questions are the same, minus the instructor branch.

See [docs/AUTENTICAZIONE.md](../docs/AUTENTICAZIONE.md) for the flow end to
end and [docs/LEGALE.md](../docs/LEGALE.md) for the notices.

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
