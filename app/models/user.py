# =============================================================================
# Professional Resume Builder — User Model
# =============================================================================
"""
User model for optional authentication.

The MVP works without auth (localStorage only), but the schema is ready
for future email/password or OAuth authentication.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.resume import Resume


class User(Base):
    """
    User account model.

    Supports:
    - Email/password authentication (future)
    - Multiple resumes per user
    - Account activation/deactivation
    """

    __tablename__ = "users"

    # --- Profile ---
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # --- Account Status ---
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # --- Relationships ---
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id!r}, email={self.email!r})>"
