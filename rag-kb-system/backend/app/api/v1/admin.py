"""Admin management API endpoints.

Provides administrative operations for user management,
system monitoring, and configuration.

Endpoints:
    GET  /admin/users: List all users
    PUT  /admin/users/{id}/role: Update user role
    PUT  /admin/users/{id}/status: Enable/disable user
    GET  /admin/stats: Get system statistics
    GET  /admin/documents: List all documents
"""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users")
async def list_users():
    """List all users (admin only).

    Returns paginated user list with roles and status.
    Supports search and role filtering.
    """
    # TODO: Implement in Phase 5
    return {"code": 0, "message": "Not implemented", "data": None}


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str):
    """Update a user's role (admin only).

    Changes the user's role for RBAC permission checking.
    Only admins can change roles.
    """
    # TODO: Implement in Phase 5
    return {"code": 0, "message": "Not implemented", "data": None}


@router.put("/users/{user_id}/status")
async def update_user_status(user_id: str):
    """Enable or disable a user account (admin only).

    Disabled accounts cannot log in or access any resources.
    """
    # TODO: Implement in Phase 5
    return {"code": 0, "message": "Not implemented", "data": None}


@router.get("/stats")
async def get_system_stats():
    """Get system statistics (admin only).

    Returns counts of users, documents, chunks, and embeddings.
    """
    # TODO: Implement in Phase 5
    return {"code": 0, "message": "Not implemented", "data": None}


@router.get("/documents")
async def list_all_documents():
    """List all documents across all users (admin only).

    Returns paginated document list with owner information.
    """
    # TODO: Implement in Phase 5
    return {"code": 0, "message": "Not implemented", "data": None}
