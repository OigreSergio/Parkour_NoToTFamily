# Contributing

## Workflow

1. Create a branch off `main`: `git checkout -b feat/<short-description>`.
2. Make focused commits. Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
3. Run the relevant checks locally before pushing:
   - Backend: `cd backend && ruff check . && pytest`
   - Mobile: `cd mobile && flutter analyze && flutter test`
   - Web admin: `cd web-admin && npm run lint && npm test`
4. Open a PR against `main`. CI must be green; one reviewer approval required.

## Branch naming

- `feat/<feature>` — new functionality
- `fix/<bug>` — bug fix
- `chore/<task>` — tooling, deps, CI
- `docs/<topic>` — docs only

## Code style

- **Python:** Ruff + Black, type hints required on public functions, async-first.
- **Dart:** `flutter_lints`, Riverpod for state, `freezed` for models.
- **TypeScript:** ESLint + Prettier, strict mode on.

## Tests

- Every new endpoint needs at least one integration test.
- Every new business rule needs a unit test.
- Mobile widgets that hold logic need a widget test.

## What not to commit

Secrets, `.env`, build artifacts, IDE configs, large binaries. The `.gitignore` is your safety net but check `git status` before committing.
