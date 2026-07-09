"""Casbin RBAC permission management.

Initializes and manages the Casbin enforcer with PostgreSQL-backed
policy storage.  Policies are loaded from the ``casbin_rules`` table
via ``casbin_sqlalchemy_adapter`` and can be hot-reloaded without
restarting the application.

Default policy layout (seeded by ``init_default_policies``)::

    admin   → *,   *,          .*        (full access)
    manager → *,   document:*, (read|create|update|delete|upload)
    manager → *,   user,       read
    user    → *,   document:*, (read|upload)
    user    → *,   document,   read
    user    → *,   search,     (read|search)

Usage::

    from app.core.security.rbac import get_enforcer, check_permission

    enforcer = await get_enforcer()
    allowed = check_permission(enforcer, "admin", "document", "upload")
"""

import logging
import os
from pathlib import Path

import casbin
from casbin_sqlalchemy_adapter import Adapter

from app.config import settings
from app.models.user import USER_ROLES

logger = logging.getLogger(__name__)

# Path to the Casbin model definition file.
_MODEL_PATH = Path(__file__).parent / "model.conf"

# Singleton enforcer instance (created once per process).
_enforcer: casbin.Enforcer | None = None


async def get_enforcer() -> casbin.Enforcer:
    """Return the process-wide Casbin enforcer, creating it on first call.

    The enforcer is backed by the ``casbin_rules`` PostgreSQL table.
    Subsequent calls return the cached instance.

    Returns:
        Initialised Casbin ``Enforcer``.
    """
    global _enforcer  # noqa: PLW0603
    if _enforcer is not None:
        return _enforcer

    adapter = Adapter(settings.db.sync_url)

    _enforcer = casbin.Enforcer(str(_MODEL_PATH), adapter)

    # Load whatever policies already exist in the database.
    _enforcer.load_policy()
    logger.info("Casbin enforcer initialised (model=%s)", _MODEL_PATH)

    return _enforcer


def check_permission(
    enforcer: casbin.Enforcer,
    role: str,
    resource: str,
    action: str,
) -> bool:
    """Check whether *role* may perform *action* on *resource*.

    Args:
        enforcer: Active Casbin enforcer.
        role: Caller role name (``admin``, ``manager``, ``user``).
        resource: Resource identifier (e.g. ``document``, ``search``).
        action: Action name (e.g. ``read``, ``upload``).

    Returns:
        ``True`` if the policy allows the action.
    """
    allowed = enforcer.enforce(role, resource, action)
    logger.debug(
        "RBAC check: role=%s resource=%s action=%s → %s",
        role, resource, action, allowed,
    )
    return allowed


async def reload_policies() -> None:
    """Hot-reload policies from the database.

    Call this after modifying the ``casbin_rules`` table so that
    changes take effect without restarting the service.
    """
    enforcer = await get_enforcer()
    enforcer.load_policy()
    logger.info("Casbin policies reloaded")


async def init_default_policies() -> None:
    """Seed default RBAC policies if none exist yet.

    This is safe to call multiple times — it only inserts policies
    when the ``casbin_rules`` table is empty.

    Policy summary:

    * **admin** — full access to every resource/action.
    * **manager** — CRUD + upload on documents; read users.
    * **user** — read + upload on documents; read + search on search.
    """
    enforcer = await get_enforcer()

    # Only seed when the table is completely empty.
    if enforcer.get_policy():
        logger.debug("Policies already exist — skipping seed")
        return

    # ── Role hierarchy ────────────────────────────────────────
    # manager inherits from user (manager can do everything user can)
    enforcer.add_role_for_user("manager", "user")
    # admin inherits from manager
    enforcer.add_role_for_user("admin", "manager")

    # ── admin policies (wildcard — full access) ──────────────
    enforcer.add_policy("admin", "*", ".*")

    # ── manager policies ─────────────────────────────────────
    enforcer.add_policy("manager", "document", "read")
    enforcer.add_policy("manager", "document", "create")
    enforcer.add_policy("manager", "document", "update")
    enforcer.add_policy("manager", "document", "delete")
    enforcer.add_policy("manager", "document", "upload")
    enforcer.add_policy("manager", "user", "read")

    # ── user policies ────────────────────────────────────────
    enforcer.add_policy("user", "document", "read")
    enforcer.add_policy("user", "document", "upload")
    enforcer.add_policy("user", "search", "read")
    enforcer.add_policy("user", "search", "search")

    logger.info("Default RBAC policies seeded")
