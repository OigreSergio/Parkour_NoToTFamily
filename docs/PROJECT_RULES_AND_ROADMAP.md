# Project rules & roadmap

This document fixes the conventions the **Parkour NoToT Family** monorepo
follows and the direction it is heading. It complements — and does not replace —
[`README.md`](../README.md), [`CONTRIBUTING.md`](../CONTRIBUTING.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md) and [`DATA_MODEL.md`](DATA_MODEL.md).

---

## 1. What this project is

A social app for the parkour community: find spots on a map, chat with traceurs
nearby, and follow curated training/recovery videos. Spots are **moderated**
before they go public.

```
.
├── backend/      FastAPI + PostgreSQL/PostGIS API   (source of truth)
├── mobile/       Flutter app (iOS + Android)         (read/consume the API)
├── web-admin/    Next.js admin dashboard             (spot moderation)
├── docs/         Architecture & product docs
└── docker-compose.yml
```

---

## 2. Golden rules

1. **The backend is the source of truth.** Data shapes, validation and business
   rules live in `backend/`. Clients mirror them, they don't invent them.
2. **Only verified spots are public.** A spot is `pending` → `verified` |
   `rejected`. The map and list show `verified` only.
3. **No upward dependencies in the backend.** API → services → repositories →
   models. Never the other way around.
4. **Every SQL query lives in a repository.** No raw DB access from API or
   service layers.
5. **Secrets never get committed.** No `.env`, tokens, keystores or build
   artifacts. Check `git status` before every commit.
6. **Migrations are append-only.** Never edit a shipped Alembic migration;
   create a new one.
7. **Focused commits, green CI.** One logical change per commit; a PR merges
   only when CI is green and one reviewer approves.

---

## 3. Conventions per stack

### Backend — Python 3.11+ (FastAPI)
- Ruff + Black. Type hints required on public functions. Async-first.
- Pydantic schemas for every request/response.
- Every new endpoint needs at least one integration test; every new business
  rule needs a unit test.
- Auth: Argon2id hashing, short-lived JWT (15 min) + rotating refresh token
  (30 days, DB-stored so it's revocable). Admin endpoints check
  `user.role == "admin"`.

### Mobile — Flutter 3.22+ (Dart)
- Lints: `flutter_lints`. State: **Riverpod**. HTTP via a single configurable
  base URL (`http://10.0.2.2:8000` for the Android emulator by default).
- Models live in `lib/models/` with `fromJson`/`toJson`. Keep them **tolerant**:
  unknown/missing fields must default, never throw.
- Client-only fields (not yet on the backend) are allowed but must be optional
  with a default, and documented as such in the model.
- `flutter analyze` and `flutter test` must pass before pushing.

### Web admin — Node 20+ (Next.js/TypeScript)
- ESLint + Prettier, `strict` mode on. `npm run lint` and `npm test` before
  pushing.

---

## 4. Git workflow

- Branch off `main`: `feat/<x>`, `fix/<x>`, `chore/<x>`, `docs/<x>`.
- [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- PR against `main`; CI green + 1 approval to merge.
- Pre-push checks:
  - Backend: `cd backend && ruff check . && pytest`
  - Mobile: `cd mobile && flutter analyze && flutter test`
  - Web admin: `cd web-admin && npm run lint && npm test`

---

## 5. Feature scope status

| Feature                | Backend | Mobile              | Web admin | Status        |
| ---------------------- | ------- | ------------------- | --------- | ------------- |
| Auth (email + JWT)     | ✅      | ⏳ planned          | ⏳        | In progress   |
| Map / list of spots    | ✅      | ✅ read-only        | —         | **Shipped**   |
| Spot detail            | ✅      | ✅                  | —         | **Shipped**   |
| Submit a spot          | ✅      | ⏳ planned          | —         | Planned       |
| Verify a spot          | ✅      | —                   | ⏳        | Planned       |
| Likes on spots         | ⏳      | ✅ client-side stub | —         | Client-first  |
| "Water nearby" flag    | ⏳      | ✅ client-side stub | ⏳        | Client-first  |
| Fountains map (Roma)   | —       | ✅ offline dataset  | —         | **Shipped**   |
| Chat                   | ✅      | ⏳ planned          | —         | Planned       |
| Videos                 | ✅      | ⏳ planned          | ⏳        | Planned       |

> **Client-first** means the mobile model already carries the field (optional,
> defaulted) so the UI can be built, but the backend does not persist it yet.
> These need a backend column + endpoint before they are real (see roadmap).

---

## 6. Roadmap

### Milestone 1 — Read-only spots ✅ (done)
Flutter client reads verified spots and shows them on a `flutter_map` map and in
a scrollable list, with a detail view. No auth required.

### Milestone 1b — Rome fountains map ✅ (done)
A second map (fountain icon in the app bar, top right) showing Rome's public
drinking fountains. The dataset cross-references the open databases behind the
popular fountain apps — OpenStreetMap via Overpass (the data used by WeTap and
Fontanelle d'Italia) and Wikidata — merged by ~30 m proximity with
per-fountain source attribution and confidence. Generated offline by
`backend/scripts/build_fountains_dataset.py` and bundled as
`mobile/assets/data/fountains_roma.json`, so the map works offline. Re-run the
script periodically to refresh the data.

### Milestone 2 — Engagement: likes & attributes (next)
- **Backend:** add `likes` (count) and per-user like tracking, plus a `water`
  boolean, to the `spots` table; expose `POST /api/v1/spots/{id}/like` and
  `DELETE /api/v1/spots/{id}/like`. Return `likes` and the caller's `liked`
  state on `GET /api/v1/spots`.
- **Mobile:** wire the existing `Spot.toggleLike()` optimistic update to the new
  endpoints; show a water indicator on the map marker and detail screen.
- **Depends on:** Milestone 3 auth (a like belongs to a user).

### Milestone 3 — Auth on mobile
Login/register flow against `POST /api/v1/auth/*`; store the JWT + refresh token
securely (`flutter_secure_storage`); attach `Authorization: Bearer` to
requests. Unlocks likes, spot submission and chat.

### Milestone 4 — Submit a spot
Mobile submit form → `POST /api/v1/spots` (`status = pending`); web-admin
moderation queue → `POST /api/v1/spots/{id}/verify` with the moderation audit
log.

### Milestone 5 — Chat
WebSocket `/api/v1/ws/chat`, conversation list + room on mobile.

### Milestone 6 — Videos
Category tabs (recovery / practice / conditioning) backed by
`GET /api/v1/videos`; web-admin CMS to curate them.

---

## 7. Definition of done (any feature)

- [ ] Backend endpoint + schema + tests, if data is involved.
- [ ] Client model stays tolerant (optional/defaulted fields).
- [ ] `flutter analyze` / `ruff` / `eslint` clean.
- [ ] Docs updated (`DATA_MODEL.md` for schema changes, this file's scope table).
- [ ] PR green + reviewed.
