# Security policy

## Reporting a vulnerability

Email **security@notot.family** (or open a private security advisory on GitHub). Do not file a public issue.

Please include:
- A clear description of the issue and its impact
- Steps to reproduce, ideally with a minimal proof-of-concept
- Your name and contact for follow-up (we will credit you in the fix unless you ask us not to)

We aim to acknowledge reports within 48 hours and ship a fix or mitigation within 14 days for high-severity issues.

## Scope

In scope: the backend API, mobile app, web admin, and CI configuration in this repository.
Out of scope: third-party services we depend on (please report to them directly), social engineering, physical attacks.

## Hardening checklist

- [x] Passwords hashed with Argon2id
- [x] JWT access tokens (short-lived) + refresh tokens (rotation on use)
- [x] Per-IP and per-account rate limiting on auth endpoints
- [x] Strict CORS allowlist
- [x] Input validation via Pydantic at every boundary
- [x] PostgreSQL queries via SQLAlchemy (no raw string interpolation)
- [x] CodeQL + Dependabot enabled
- [ ] Bug bounty program (planned)
