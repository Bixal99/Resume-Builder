# =============================================================================
# Professional Resume Builder — Base Model
# =============================================================================
"""
SQLAlchemy declarative base with common mixins.

All models inherit from Base and get:
- UUID primary key
- created_at / updated_at timestamps
- Consistent table naming
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy models.

    Provides:
    - `id`: UUID string primary key (auto-generated)
    - `created_at`: Timestamp when the row was created
    - `updated_at`: Timestamp when the row was last updated
    """

    # UUID primary key — stored as a 36-char string for SQLite compatibility
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # Automatic timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Generic repr showing class name and ID."""
        return f"<{self.__class__.__name__}(id={self.id!r})>"
