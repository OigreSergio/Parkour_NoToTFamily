from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, log
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.repositories import users as users_repo

settings = get_settings()
configure_logging(debug=settings.debug)

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


async def _ensure_initial_admin() -> None:
    """Create the INITIAL_ADMIN_* user on startup if it doesn't exist yet."""
    if not (settings.initial_admin_email and settings.initial_admin_password):
        return
    async with SessionLocal() as session:
        existing = await users_repo.get_by_email(session, settings.initial_admin_email)
        if existing is not None:
            return
        session.add(
            User(
                email=settings.initial_admin_email.lower(),
                password_hash=hash_password(settings.initial_admin_password),
                display_name="Admin",
                role=UserRole.admin,
                is_email_verified=True,
            )
        )
        await session.commit()
        log.info("initial_admin_created", email=settings.initial_admin_email)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", env=settings.env)
    await _ensure_initial_admin()
    yield
    log.info("shutdown")


app = FastAPI(
    title="Parkour NoToT Family API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.env != "production" else None,
    redoc_url=None,
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"] if settings.env != "production" else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429, content={"error": {"code": "rate_limited", "message": str(exc.detail)}}
    )


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
