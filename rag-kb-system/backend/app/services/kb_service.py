"""Knowledge Base management service.

Handles KB CRUD, document association, and visibility checks.

Usage:
    from app.services.kb_service import KBService

    service = KBService(db_session)
    kb = await service.create_kb(user_id, name="My KB")
"""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    AuthorizationError,
    DocumentNotFoundError,
    NotFoundError,
    ValidationError,
)
from app.models.document import Document
from app.models.knowledge_base import KBDocument, KBVisibility, KnowledgeBase
from app.models.user import User

logger = logging.getLogger(__name__)


class KBService:
    """Knowledge Base management service.

    Attributes:
        db: Async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize KB service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create_kb(
        self,
        owner_id: uuid.UUID,
        name: str,
        description: str | None = None,
        visibility: str = "private",
    ) -> KnowledgeBase:
        """Create a new knowledge base.

        Args:
            owner_id: Owner user UUID.
            name: KB name.
            description: Optional description.
            visibility: Access level (public/private/dept).

        Returns:
            Created KnowledgeBase instance.
        """
        kb = KnowledgeBase(
            name=name,
            description=description,
            owner_id=owner_id,
            visibility=KBVisibility(visibility),
        )
        self.db.add(kb)
        await self.db.flush()

        logger.info("Knowledge base created: %s (%s) by user %s", kb.id, name, owner_id)
        return kb

    async def get_kb(
        self,
        kb_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> KnowledgeBase:
        """Get knowledge base by ID with visibility check.

        Args:
            kb_id: KB UUID.
            user_id: Requesting user UUID (for visibility check).

        Returns:
            KnowledgeBase instance.

        Raises:
            NotFoundError: If KB not found.
            AuthorizationError: If user lacks access.
        """
        result = await self.db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.is_deleted == False,  # noqa: E712
            )
        )
        kb = result.scalar_one_or_none()

        if kb is None:
            raise NotFoundError(resource="KnowledgeBase", identifier=str(kb_id))

        # Visibility check
        if user_id is not None:
            await self._check_visibility(kb, user_id)

        return kb

    async def list_kbs(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[KnowledgeBase], int]:
        """List knowledge bases accessible to the user.

        Returns KBs where:
        - visibility is PUBLIC, or
        - visibility is DEPT and user is in the same dept, or
        - user is the owner

        Args:
            user_id: Requesting user UUID.
            page: Page number (1-based).
            page_size: Items per page.

        Returns:
            Tuple of (KBs list, total count).
        """
        # Get user's department
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        user_dept = user.dept_id if user else None

        # Build visibility filter
        visibility_filter = (
            (KnowledgeBase.visibility == KBVisibility.PUBLIC)
            | (KnowledgeBase.owner_id == user_id)
        )
        if user_dept is not None:
            visibility_filter = visibility_filter | (
                (KnowledgeBase.visibility == KBVisibility.DEPT)
                & (KnowledgeBase.owner_id.in_(
                    select(User.id).where(User.dept_id == user_dept)
                ))
            )

        query = select(KnowledgeBase).where(
            KnowledgeBase.is_deleted == False,  # noqa: E712
            visibility_filter,
        )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        query = query.order_by(KnowledgeBase.created_at.desc())
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        kbs = list(result.scalars().all())

        return kbs, total

    async def update_kb(
        self,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        visibility: str | None = None,
    ) -> KnowledgeBase:
        """Update knowledge base metadata.

        Args:
            kb_id: KB UUID.
            user_id: Requesting user UUID (must be owner or admin).
            name: New name (None to skip).
            description: New description (None to skip).
            visibility: New visibility (None to skip).

        Returns:
            Updated KnowledgeBase instance.

        Raises:
            NotFoundError: If KB not found.
            AuthorizationError: If user is not the owner.
        """
        kb = await self.get_kb(kb_id)
        await self._check_ownership(kb, user_id)

        if name is not None:
            kb.name = name
        if description is not None:
            kb.description = description
        if visibility is not None:
            kb.visibility = KBVisibility(visibility)

        await self.db.flush()
        await self.db.refresh(kb)

        logger.info("Knowledge base updated: %s by user %s", kb_id, user_id)
        return kb

    async def delete_kb(
        self,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Soft delete a knowledge base.

        Does NOT delete associated documents — only removes the
        KB and its document associations.

        Args:
            kb_id: KB UUID.
            user_id: Requesting user UUID.

        Raises:
            NotFoundError: If KB not found.
            AuthorizationError: If user is not the owner.
        """
        kb = await self.get_kb(kb_id)
        await self._check_ownership(kb, user_id)

        # Remove all document associations
        await self.db.execute(
            select(KBDocument).where(KBDocument.kb_id == kb_id)
        )
        from sqlalchemy import delete
        await self.db.execute(
            delete(KBDocument).where(KBDocument.kb_id == kb_id)
        )

        kb.soft_delete()
        await self.db.flush()

        logger.info("Knowledge base deleted: %s by user %s", kb_id, user_id)

    async def add_documents(
        self,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
    ) -> int:
        """Add documents to a knowledge base.

        Silently skips documents that are already associated or
        don't exist.

        Args:
            kb_id: KB UUID.
            user_id: Requesting user UUID.
            document_ids: List of document UUIDs to add.

        Returns:
            Number of documents actually added.

        Raises:
            NotFoundError: If KB not found.
            AuthorizationError: If user is not the owner.
        """
        kb = await self.get_kb(kb_id)
        await self._check_ownership(kb, user_id)

        # Get existing associations
        existing_result = await self.db.execute(
            select(KBDocument.document_id).where(
                KBDocument.kb_id == kb_id,
                KBDocument.document_id.in_(document_ids),
            )
        )
        existing_ids = {row[0] for row in existing_result.all()}

        # Get valid documents
        valid_result = await self.db.execute(
            select(Document.id).where(
                Document.id.in_(document_ids),
                Document.is_deleted == False,  # noqa: E712
            )
        )
        valid_ids = {row[0] for row in valid_result.all()}

        added = 0
        for doc_id in document_ids:
            if doc_id in existing_ids or doc_id not in valid_ids:
                continue
            self.db.add(KBDocument(kb_id=kb_id, document_id=doc_id))
            added += 1

        await self.db.flush()

        logger.info("Added %d documents to KB %s", added, kb_id)
        return added

    async def remove_documents(
        self,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID],
    ) -> int:
        """Remove documents from a knowledge base.

        Args:
            kb_id: KB UUID.
            user_id: Requesting user UUID.
            document_ids: List of document UUIDs to remove.

        Returns:
            Number of documents actually removed.

        Raises:
            NotFoundError: If KB not found.
            AuthorizationError: If user is not the owner.
        """
        kb = await self.get_kb(kb_id)
        await self._check_ownership(kb, user_id)

        from sqlalchemy import delete

        result = await self.db.execute(
            delete(KBDocument).where(
                KBDocument.kb_id == kb_id,
                KBDocument.document_id.in_(document_ids),
            )
        )
        await self.db.flush()

        removed = result.rowcount or 0
        logger.info("Removed %d documents from KB %s", removed, kb_id)
        return removed

    async def list_kb_documents(
        self,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """List documents in a knowledge base.

        Args:
            kb_id: KB UUID.
            user_id: Requesting user UUID.
            page: Page number (1-based).
            page_size: Items per page.

        Returns:
            Tuple of (documents list, total count).

        Raises:
            NotFoundError: If KB not found.
            AuthorizationError: If user lacks access.
        """
        kb = await self.get_kb(kb_id, user_id)

        # Query documents via association
        query = (
            select(Document)
            .join(KBDocument, KBDocument.document_id == Document.id)
            .where(
                KBDocument.kb_id == kb_id,
                Document.is_deleted == False,  # noqa: E712
            )
        )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        offset = (page - 1) * page_size
        query = query.order_by(Document.created_at.desc())
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        documents = list(result.scalars().all())

        return documents, total

    # ── Visibility helpers ─────────────────────────────────────

    async def _check_visibility(self, kb: KnowledgeBase, user_id: uuid.UUID) -> None:
        """Check if user can access the KB based on visibility.

        Args:
            kb: Knowledge base to check.
            user_id: Requesting user UUID.

        Raises:
            AuthorizationError: If access is denied.
        """
        if kb.visibility == KBVisibility.PUBLIC:
            return

        if kb.owner_id == user_id:
            return

        if kb.visibility == KBVisibility.DEPT:
            # Check if same department
            owner_result = await self.db.execute(
                select(User.dept_id).where(User.id == kb.owner_id)
            )
            owner_dept = owner_result.scalar_one_or_none()

            user_result = await self.db.execute(
                select(User.dept_id).where(User.id == user_id)
            )
            user_dept = user_result.scalar_one_or_none()

            if owner_dept is not None and owner_dept == user_dept:
                return

        raise AuthorizationError(
            detail="You don't have access to this knowledge base"
        )

    async def _check_ownership(self, kb: KnowledgeBase, user_id: uuid.UUID) -> None:
        """Check if user is the owner or an admin.

        Args:
            kb: Knowledge base to check.
            user_id: Requesting user UUID.

        Raises:
            AuthorizationError: If user is not the owner.
        """
        if kb.owner_id == user_id:
            return

        # Check if admin
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if user is not None and user.is_admin:
            return

        raise AuthorizationError(
            detail="Only the owner or admin can modify this knowledge base"
        )
