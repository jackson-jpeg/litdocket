from fastapi import APIRouter
from app.api.v1 import auth, documents, cases, deadlines, chat, dashboard, triggers, search, insights, verification

api_router = APIRouter()

# Authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Protected routes
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(deadlines.router, prefix="/deadlines", tags=["deadlines"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(triggers.router, prefix="/triggers", tags=["triggers"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
# Case OS: Verification gate
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])
