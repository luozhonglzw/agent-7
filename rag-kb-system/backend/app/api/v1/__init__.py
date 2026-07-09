"""API v1 routes package.

Contains all version 1 API endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1 import auth, documents, knowledge_bases, search, admin, audit

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(knowledge_bases.router)
api_v1_router.include_router(search.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(audit.router)
