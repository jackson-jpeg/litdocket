from fastapi import APIRouter
from app.api.v1 import documents, cases, deadlines, chat, dashboard

api_router = APIRouter()

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(deadlines.router, prefix="/deadlines", tags=["deadlines"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
