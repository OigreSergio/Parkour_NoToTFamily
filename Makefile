.PHONY: help up down logs api-shell db-shell migrate seed-spots seed-videos test lint format

help:
	@echo "Common targets:"
	@echo "  up         Bring the full stack up (db, redis, api, web-admin)"
	@echo "  down       Stop the stack"
	@echo "  logs       Tail logs"
	@echo "  migrate    Apply DB migrations"
	@echo "  seed-spots Load backend/seeds/spots.json as verified spots"
	@echo "  seed-videos Load backend/seeds/videos.json as the tutorial catalog"
	@echo "  test       Run backend tests"
	@echo "  lint       Run linters across the repo"
	@echo "  format     Auto-format Python + JS/TS"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

api-shell:
	docker compose exec api sh

db-shell:
	docker compose exec db psql -U parkour

migrate:
	docker compose exec api alembic upgrade head

seed-spots:
	docker compose exec api python -m app.db.seed_spots

seed-videos:
	docker compose exec api python -m app.db.seed_videos

test:
	cd backend && pytest

lint:
	cd backend && ruff check .
	cd web-admin && npm run lint
	cd mobile && flutter analyze

format:
	cd backend && ruff format . && ruff check . --fix
	cd web-admin && npm run format
