# Architecture

## High-level

```
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
│  Flutter app │      │  Web admin   │      │  External: OSM   │
│  (iOS/Andr.) │      │  (Next.js)   │      │  tiles, S3, etc. │
└──────┬───────┘      └──────┬───────┘      └────────┬─────────┘
       │ HTTPS + WS         │ HTTPS                  │
       └──────────┬─────────┘                        │
                  ▼                                  │
          ┌───────────────┐                          │
          │  FastAPI app  │◄─────────────────────────┘
          │   (uvicorn)   │
          └───┬──────┬────┘
              │      │
        ┌─────▼──┐ ┌─▼──────┐
        │ PG +   │ │ Redis  │  (cache, rate-limit, pub/sub for chat)
        │ PostGIS│ └────────┘
        └────────┘
```

## Backend layers

| Layer            | Folder                | Responsibility                                              |
| ---------------- | --------------------- | ----------------------------------------------------------- |
| API              | `app/api/v1/`         | HTTP/WS handlers, request/response shape                    |
| Schemas          | `app/schemas/`        | Pydantic models for request/response validation             |
| Services         | `app/services/`       | Business rules (spot verification, chat dispatch)           |
| Repositories     | `app/repositories/`   | DB access — every SQL query lives here                      |
| Models           | `app/models/`         | SQLAlchemy ORM models                                       |
| Core             | `app/core/`           | Config, security, logging, exception handlers               |

API depends on schemas and services. Services depend on repositories. Repositories depend on models. **No upward dependencies.**

## Data model (high level)

- `users(id, email, password_hash, display_name, role, created_at)`
- `spots(id, name, description, location GEOGRAPHY(Point), photos[], submitted_by, status, verified_by, verified_at, created_at)`
- `conversations(id, kind, created_at)` / `conversation_members(conversation_id, user_id)`
- `messages(id, conversation_id, author_id, body, created_at)`
- `videos(id, title, url, category, level, created_at)`

See [DATA_MODEL.md](DATA_MODEL.md) for the full schema.

## Auth

- Argon2id password hashing.
- `POST /auth/login` returns a short-lived JWT (15 min) + refresh token (30 days, rotates on use, stored in DB so it can be revoked).
- All non-public endpoints require `Authorization: Bearer <jwt>`.
- Admin-only endpoints check `user.role == "admin"`.

## Chat

WebSocket at `/api/v1/ws/chat`. On connect, the client sends `{ "type": "auth", "token": "<jwt>" }`. Messages are persisted then fanned out via Redis pub/sub so multiple uvicorn workers stay consistent.

## Spot verification

See [SPOT_VERIFICATION.md](SPOT_VERIFICATION.md).
