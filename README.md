# Parkour NoToT Family

A social app for the parkour community: find spots on a map, chat with traceurs nearby, and follow curated training and recovery videos. Spots are reviewed before they go public.

## Monorepo layout

```
.
├── backend/      FastAPI + PostgreSQL/PostGIS API
├── mobile/       Flutter app (iOS + Android)
├── web-admin/    Next.js admin dashboard (spot moderation, backup panel)
├── docs/         Architecture and product docs
├── scripts/      Repo-level tooling (backup manifest generator)
├── 📲/           24h-rotating backup manifest + direct links (see 📲/BACKUP.md)
├── .github/      CI workflows (daily backup), dependabot
└── docker-compose.yml
```

## Backup

Every 24 hours the `Daily backup` workflow destroys and regenerates
[`📲/backup-latest.json`](📲/backup-latest.json) (all branches + dataset
checksums, with direct download links) and uploads a full `git bundle` of the
repository as a 1-day-retention artifact. Direct links and restore steps:
[`📲/BACKUP.md`](📲/BACKUP.md). Admins also get a live view at `/backup` in
the web-admin dashboard.

## Core features

| Feature             | Backend                                    | Mobile        | Web admin |
| ------------------- | ------------------------------------------ | ------------- | --------- |
| Auth (email + JWT)  | `POST /api/v1/auth/*`                      | Login flow    | Login     |
| Map / spots         | `GET /api/v1/spots`, geo search via PostGIS | Map screen    | —         |
| Submit a spot       | `POST /api/v1/spots` (status = `pending`)  | Submit form   | —         |
| Verify a spot       | `POST /api/v1/spots/{id}/verify` (admin)   | —             | Queue UI  |
| Fountains map (Roma) | dataset script (OSM × Wikidata merge)     | Fountains map | —         |
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).
