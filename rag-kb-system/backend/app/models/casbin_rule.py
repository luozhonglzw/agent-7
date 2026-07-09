"""CasbinRule SQLAlchemy model for RBAC policy storage.

Stores Casbin RBAC policies in PostgreSQL for persistence
across application restarts.

Table:
    casbin_rules: Casbin policy rules.
"""

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CasbinRule(Base):
    """Casbin RBAC policy rule.

    Stores Casbin policy definitions in the database.
    Compatible with casbin-sqlalchemy-adapter.

    Attributes:
        id: Auto-increment primary key.
        ptype: Policy type (p, g, g2, etc.).
        v0: First policy field (typically user/role).
        v1: Second policy field (typically resource/permission).
        v2: Third policy field (typically action).
        v3: Fourth policy field.
        v4: Fifth policy field.
        v5: Sixth policy field.
    """

    __tablename__ = "casbin_rules"
    __table_args__ = (
        Index("ix_casbin_rules_ptype", "ptype"),
        Index("ix_casbin_rules_v0v1", "v0", "v1"),
        {"comment": "Casbin RBAC policy rules"},
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="Auto-increment primary key",
    )
    ptype: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="Policy type (p, g, g2, etc.)",
    )
    v0: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="First policy field",
    )
    v1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="Second policy field",
    )
    v2: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="Third policy field",
    )
    v3: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="Fourth policy field",
    )
    v4: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="Fifth policy field",
    )
    v5: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="Sixth policy field",
    )

    def __repr__(self) -> str:
        return (
            f"<CasbinRule(id={self.id}, ptype='{self.ptype}', "
            f"v0='{self.v0}', v1='{self.v1}')>"
        )
