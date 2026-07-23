from fastapi import APIRouter

from app.api.v1 import admin, auth, chat, spots, users, videos, ws

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(spots.router)
api_router.include_router(admin.router)
api_router.include_router(chat.router)
api_router.include_router(videos.router)
api_router.include_router(ws.router)
