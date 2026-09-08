# =============================================================================
# Professional Resume Builder — User Pydantic Schemas
# =============================================================================
"""
User schemas for future authentication support.

Currently minimal — designed to be extended when auth is implemented.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Shared user fields."""
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    """Schema for user API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
