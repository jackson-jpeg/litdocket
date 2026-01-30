from fastapi import APIRouter
from app.api.v1 import (
    auth, documents, cases, deadlines, chat, chat_stream, dashboard, triggers,
    search, insights, verification, notifications, jurisdictions,
    rag_search, workload, rules, audit, authority_core, health
)

api_router = APIRouter()

# Authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Protected routes
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(deadlines.router, prefix="/deadlines", tags=["deadlines"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(chat_stream.router, prefix="/chat", tags=["chat-streaming"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(triggers.router, prefix="/triggers", tags=["triggers"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
api_router.include_router(notifications.router, tags=["notifications"])
# Case OS: Verification gate
api_router.include_router(verification.router, prefix="/verification", tags=["verification"])

# Jurisdiction and Rule System
api_router.include_router(jurisdictions.router, tags=["jurisdictions"])

# Phase 1 Features: AI-Powered Intelligence
api_router.include_router(rag_search.router, prefix="/rag", tags=["rag-semantic-search"])
api_router.include_router(workload.router, prefix="/workload", tags=["workload-optimization"])

# User-Created Rules System
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])

# Audit Trail & AI Staging
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])

# Authority Core - AI-Powered Rules Database
api_router.include_router(authority_core.router, tags=["authority-core"])

# Health Check Endpoints
api_router.include_router(health.router, tags=["health"])
