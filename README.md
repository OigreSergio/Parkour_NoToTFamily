# Parkour NoToT Family

A social app for the parkour community: find spots on a map, chat with traceurs nearby, and follow curated training and recovery videos. Spots are reviewed before they go public.

## Monorepo layout

```
.
├── backend/      FastAPI + PostgreSQL/PostGIS API
├── mobile/       Flutter app (iOS + Android)
├── web-admin/    Next.js admin dashboard (spot moderation)
├── docs/         Architecture and product docs
├── .github/      CI workflows, issue/PR templates, dependabot
└── docker-compose.yml
```

## Core features

| Feature             | Backend                                    | Mobile        | Web admin |
| ------------------- | ------------------------------------------ | ------------- | --------- |
| Auth (email + JWT)  | `POST /api/v1/auth/*`                      | Login flow    | Login     |
| Map / spots         | `GET /api/v1/spots`, geo search via PostGIS | Map screen    | —         |
| Submit a spot       | `POST /api/v1/spots` (status = `pending`)  | Submit form   | —         |
| Verify a spot       | `POST /api/v1/spots/{id}/verify` (admin)   | —             | Queue UI  |
| Chat                | WebSocket `/api/v1/ws/chat`                | Chat screen   | —         |
| Videos              | `GET /api/v1/videos`                        | Videos screen | CMS       |

## Spot lifecycle

```
user submits  →  status=pending  →  admin reviews  →  status=verified | rejected
                                                    └─ only verified spots appear on the map
```

## Getting started

```bash
# 1. Backend (Python 3.11+)
cd backend
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# 2. Mobile (Flutter 3.22+)
cd mobile
flutter pub get
flutter run

# 3. Web admin (Node 20+)
cd web-admin
npm install
npm run dev

# Or bring everything up with Docker
docker compose up --build
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/SPOT_VERIFICATION.md](docs/SPOT_VERIFICATION.md) for details.

## Going public

The app is currently a private preview. The plan for the public launch on `pkfamily.app` — hosting, domain, access levels, and EU legal/privacy compliance — is in [docs/LAUNCH_PLAN.md](docs/LAUNCH_PLAN.md), with the executable prompt in [docs/LAUNCH_PROMPT.md](docs/LAUNCH_PROMPT.md) and build/deploy steps in [docs/DEPLOY.md](docs/DEPLOY.md).

**The web app now builds from Flutter** (`mobile/`), and Supabase is the production backend — `backend/` (FastAPI) stays in the repo as a domain reference but is not deployed, and no code path reaches it. Beware that `supabase/migrations/0001`–`0002` describe a schema that was never applied in production; the real one is reconstructed in `supabase/migrations/0003_production_baseline.sql`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).
