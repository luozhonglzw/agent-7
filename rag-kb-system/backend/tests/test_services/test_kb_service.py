"""KnowledgeBase service unit tests.

Tests for KB CRUD, document association, and visibility checks.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AuthorizationError, NotFoundError
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KBVisibility, KnowledgeBase
from app.models.user import User
from app.services.kb_service import KBService


@pytest_asyncio.fixture
def service(db_session: AsyncSession) -> KBService:
    """Create KBService with test session."""
    return KBService(db_session)


@pytest_asyncio.fixture
async def sample_kb(db_session: AsyncSession, test_user: User) -> KnowledgeBase:
    """Create a sample knowledge base."""
    kb = KnowledgeBase(
        name="Test KB",
        description="A test knowledge base",
        owner_id=test_user.id,
        visibility=KBVisibility.PRIVATE,
    )
    db_session.add(kb)
    await db_session.commit()
    await db_session.refresh(kb)
    return kb


@pytest_asyncio.fixture
async def sample_document(db_session: AsyncSession, test_user: User) -> Document:
    """Create a sample document."""
    doc = Document(
        user_id=test_user.id,
        owner_id=test_user.id,
        title="Test Doc",
        filename="test.txt",
        file_path="/tmp/test.txt",
        file_size=100,
        file_type=".txt",
        status=DocumentStatus.READY,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


class TestCreateKB:
    """Tests for KBService.create_kb."""

    async def test_create_kb(
        self, service: KBService, test_user: User
    ) -> None:
        """Test creating a knowledge base."""
        kb = await service.create_kb(
            owner_id=test_user.id,
            name="My KB",
            description="Description",
            visibility="private",
        )

        assert kb.name == "My KB"
        assert kb.description == "Description"
        assert kb.visibility == KBVisibility.PRIVATE
        assert kb.owner_id == test_user.id

    async def test_create_public_kb(
        self, service: KBService, test_user: User
    ) -> None:
        """Test creating a public KB."""
        kb = await service.create_kb(
            owner_id=test_user.id,
            name="Public KB",
            visibility="public",
        )

        assert kb.visibility == KBVisibility.PUBLIC
        assert kb.is_public is True


class TestGetKB:
    """Tests for KBService.get_kb."""

    async def test_get_own_kb(
        self, service: KBService, sample_kb: KnowledgeBase, test_user: User
    ) -> None:
        """Test getting own KB."""
        kb = await service.get_kb(sample_kb.id, test_user.id)
        assert kb.id == sample_kb.id

    async def test_get_nonexistent_kb(
        self, service: KBService
    ) -> None:
        """Test getting nonexistent KB raises error."""
        with pytest.raises(NotFoundError):
            await service.get_kb(uuid.uuid4())

    async def test_get_private_kb_other_user(
        self, service: KBService, sample_kb: KnowledgeBase, admin_user: User
    ) -> None:
        """Test getting private KB as non-owner raises error."""
        with pytest.raises(AuthorizationError):
            await service.get_kb(sample_kb.id, admin_user.id)


class TestListKBs:
    """Tests for KBService.list_kbs."""

    async def test_list_empty(
        self, service: KBService, test_user: User
    ) -> None:
        """Test listing when no KBs exist."""
        kbs, total = await service.list_kbs(test_user.id)
        assert kbs == []
        assert total == 0

    async def test_list_own_kb(
        self, service: KBService, sample_kb: KnowledgeBase, test_user: User
    ) -> None:
        """Test listing includes own KBs."""
        kbs, total = await service.list_kbs(test_user.id)
        assert total >= 1
        assert any(k.id == sample_kb.id for k in kbs)

    async def test_list_includes_public(
        self, service: KBService, test_user: User, admin_user: User
    ) -> None:
        """Test listing includes public KBs from other users."""
        # Create a public KB as admin
        await service.create_kb(
            owner_id=admin_user.id,
            name="Admin Public KB",
            visibility="public",
        )

        # test_user should see it
        kbs, total = await service.list_kbs(test_user.id)
        assert any(k.name == "Admin Public KB" for k in kbs)


class TestUpdateKB:
    """Tests for KBService.update_kb."""

    async def test_update_name(
        self, service: KBService, sample_kb: KnowledgeBase, test_user: User
    ) -> None:
        """Test updating KB name."""
        kb = await service.update_kb(
            sample_kb.id, test_user.id, name="New Name"
        )
        assert kb.name == "New Name"

    async def test_update_visibility(
        self, service: KBService, sample_kb: KnowledgeBase, test_user: User
    ) -> None:
        """Test updating KB visibility."""
        kb = await service.update_kb(
            sample_kb.id, test_user.id, visibility="public"
        )
        assert kb.visibility == KBVisibility.PUBLIC

    async def test_update_not_owner(
        self, service: KBService, sample_kb: KnowledgeBase, admin_user: User
    ) -> None:
        """Test updating as non-owner raises error (admin can update)."""
        # Admin should be able to update
        kb = await service.update_kb(
            sample_kb.id, admin_user.id, name="Admin Updated"
        )
        assert kb.name == "Admin Updated"


class TestDeleteKB:
    """Tests for KBService.delete_kb."""

    async def test_delete_own_kb(
        self, service: KBService, sample_kb: KnowledgeBase, test_user: User
    ) -> None:
        """Test deleting own KB."""
        await service.delete_kb(sample_kb.id, test_user.id)

        with pytest.raises(NotFoundError):
            await service.get_kb(sample_kb.id)


class TestDocumentAssociation:
    """Tests for KB document association."""

    async def test_add_documents(
        self,
        service: KBService,
        sample_kb: KnowledgeBase,
        sample_document: Document,
        test_user: User,
    ) -> None:
        """Test adding documents to a KB."""
        added = await service.add_documents(
            sample_kb.id, test_user.id, [sample_document.id]
        )
        assert added == 1

    async def test_add_duplicate_documents(
        self,
        service: KBService,
        sample_kb: KnowledgeBase,
        sample_document: Document,
        test_user: User,
    ) -> None:
        """Test adding same document twice skips duplicate."""
        await service.add_documents(
            sample_kb.id, test_user.id, [sample_document.id]
        )
        added = await service.add_documents(
            sample_kb.id, test_user.id, [sample_document.id]
        )
        assert added == 0

    async def test_remove_documents(
        self,
        service: KBService,
        sample_kb: KnowledgeBase,
        sample_document: Document,
        test_user: User,
    ) -> None:
        """Test removing documents from a KB."""
        await service.add_documents(
            sample_kb.id, test_user.id, [sample_document.id]
        )
        removed = await service.remove_documents(
            sample_kb.id, test_user.id, [sample_document.id]
        )
        assert removed == 1

    async def test_list_kb_documents(
        self,
        service: KBService,
        sample_kb: KnowledgeBase,
        sample_document: Document,
        test_user: User,
    ) -> None:
        """Test listing documents in a KB."""
        await service.add_documents(
            sample_kb.id, test_user.id, [sample_document.id]
        )

        docs, total = await service.list_kb_documents(
            sample_kb.id, test_user.id
        )
        assert total == 1
        assert docs[0].id == sample_document.id


class TestKBModel:
    """Tests for KnowledgeBase model."""

    def test_kb_visibility_enum(self) -> None:
        """Test KBVisibility enum values."""
        assert KBVisibility.PUBLIC.value == "public"
        assert KBVisibility.PRIVATE.value == "private"
        assert KBVisibility.DEPT.value == "dept"

    def test_kb_is_public_property(self) -> None:
        """Test is_public property."""
        kb = KnowledgeBase(
            name="Test",
            owner_id=uuid.uuid4(),
            visibility=KBVisibility.PUBLIC,
        )
        assert kb.is_public is True

        kb.visibility = KBVisibility.PRIVATE
        assert kb.is_public is False
