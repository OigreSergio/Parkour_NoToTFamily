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
| Auth (emailed code) | `POST /api/v1/auth/email/*`                | Login flow    | Login     |
| Anonymous accounts  | `POST /api/v1/auth/guest`, `/guest/resume` | —             | —         |
| Onboarding profile  | `GET/POST /api/v1/onboarding/*`            | —             | —         |
| Risk notices        | `GET /api/v1/legal/documents`              | Blocking dialogs | —      |
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

## Signing in

No password: the address is the account. A six-digit code is generated on the
spot and mailed from a no-reply sender; typing it back either signs the member
in or creates the account. Before the account exists, the risk notice has to be
accepted — it states that responsibility for an injury at a listed spot or
while following a tutorial is the user's alone, and that the platform only
undertakes to make the information available free of charge and easy to reach.

What the app asks next (date of birth, athlete or instructor, years of
practice, the vault-naming game) is driven by the server. Accounts under 18 get
a content ceiling that no answer can lift, and no client can tell it is there.

You can also come in without saying anything: an anonymous account is asked
nothing about itself — the name is generated — but answers the same questions,
because it gets the same spots and the same tutorials. It is handed a key at
sign-up, which is the only way back to it and to the progress on it. A guest is
an athlete: qualifying as an instructor means mailing a certificate and an
identity document to a human, which is the opposite of staying anonymous.

See [docs/AUTENTICAZIONE.md](docs/AUTENTICAZIONE.md) and
[docs/LEGALE.md](docs/LEGALE.md).

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/SPOT_VERIFICATION.md](docs/SPOT_VERIFICATION.md) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).
