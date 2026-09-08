# =============================================================================
# Professional Resume Builder — Resume Service
# =============================================================================
"""
Business logic for resume operations.

Orchestrates between the repository (data access) and the API layer.
Handles validation, sanitization, and data transformation.
"""

import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import sanitize_text, sanitize_url
from app.models.resume import Resume
from app.repositories.resume_repository import ResumeRepository
from app.schemas.resume import (
    ResumeCreate,
    ResumeData,
    ResumeResponse,
    ResumeUpdate,
)


class ResumeService:
    """
    Service layer for resume business logic.

    Responsibilities:
    - Input sanitization
    - Data validation beyond Pydantic
    - Coordinating repository operations
    - Converting between ORM models and schemas
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ResumeRepository(db)

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    async def create_resume(self, data: ResumeCreate) -> ResumeResponse:
        """
        Create a new resume.

        Sanitizes all text inputs before storage.
        """
        sanitized = self._sanitize_resume_data(data)
        resume = await self.repo.create(sanitized)
        return self._to_response(resume)

    async def get_resume(self, resume_id: str) -> Optional[ResumeResponse]:
        """Fetch a resume by ID."""
        resume = await self.repo.get_by_id(resume_id)
        if not resume:
            return None
        return self._to_response(resume)

    async def get_resume_by_session(
        self, session_id: str
    ) -> Optional[ResumeResponse]:
        """Fetch the most recent resume for an anonymous session."""
        resume = await self.repo.get_by_session_id(session_id)
        if not resume:
            return None
        return self._to_response(resume)

    async def update_resume(
        self, resume_id: str, data: ResumeUpdate
    ) -> Optional[ResumeResponse]:
        """
        Update an existing resume.

        Sanitizes inputs and uses replace-all strategy for sections.
        """
        sanitized = self._sanitize_resume_update(data)
        resume = await self.repo.update(resume_id, sanitized)
        if not resume:
            return None
        return self._to_response(resume)

    async def delete_resume(self, resume_id: str) -> bool:
        """Delete a resume and all its sections."""
        return await self.repo.delete(resume_id)

    async def list_resumes(self, user_id: str) -> list[ResumeResponse]:
        """List all resumes for a user."""
        resumes = await self.repo.list_by_user(user_id)
        return [self._to_response(r) for r in resumes]

    # =========================================================================
    # Data Conversion
    # =========================================================================

    def _to_response(self, resume: Resume) -> ResumeResponse:
        """
        Convert an ORM Resume model to a ResumeResponse schema.

        Handles JSON deserialization of list fields (achievements, technologies, etc.)
        """
        data = {
            "id": resume.id,
            "session_id": resume.session_id,
            "title": resume.title,
            "template_id": resume.template_id,
            "page_size": resume.page_size,
            "section_order": self._parse_json_list(resume.section_order) if getattr(resume, "section_order", None) else [],
            "hidden_sections": self._parse_json_list(resume.hidden_sections) if getattr(resume, "hidden_sections", None) else [],
            "theme_settings": self._parse_json_dict(resume.theme_settings) if getattr(resume, "theme_settings", None) else {},
            "photo": resume.photo,
            "first_name": resume.first_name,
            "last_name": resume.last_name,
            "professional_title": resume.professional_title,
            "email": resume.email,
            "phone": resume.phone,
            "address": resume.address,
            "linkedin": resume.linkedin,
            "github": resume.github,
            "portfolio": resume.portfolio,
            "website": resume.website,
            "nationality": resume.nationality,
            "summary": resume.summary,
            "created_at": resume.created_at,
            "updated_at": resume.updated_at,
            "education": [
                {**self._model_to_dict(e)} for e in resume.education
            ],
            "experience": [
                {
                    **self._model_to_dict(e),
                    "achievements": self._parse_json_list(e.achievements),
                }
                for e in resume.experience
            ],
            "projects": [
                {
                    **self._model_to_dict(p),
                    "technologies": self._parse_json_list(p.technologies),
                    "highlights": self._parse_json_list(p.highlights),
                }
                for p in resume.projects
            ],
            "skills": [self._model_to_dict(s) for s in resume.skills],
            "languages": [self._model_to_dict(l) for l in resume.languages],
            "certifications": [
                self._model_to_dict(c) for c in resume.certifications
            ],
            "awards": [self._model_to_dict(a) for a in resume.awards],
            "volunteer": [self._model_to_dict(v) for v in resume.volunteer],
            "references": [self._model_to_dict(r) for r in resume.references],
        }
        return ResumeResponse(**data)

    @staticmethod
    def _model_to_dict(model) -> dict:
        """Convert an ORM model to a dict, excluding internal fields."""
        exclude = {"resume_id", "resume", "created_at", "updated_at"}
        return {
            k: v
            for k, v in model.__dict__.items()
            if not k.startswith("_") and k not in exclude
        }

    @staticmethod
    def _parse_json_list(value: Optional[str]) -> list[str]:
        """Parse a JSON-encoded list string, returning empty list on failure."""
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _parse_json_dict(value: Optional[str]) -> dict:
        """Parse a JSON-encoded dict string, returning empty dict on failure."""
        if not value:
            return {}
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def resume_to_data(self, response: ResumeResponse) -> ResumeData:
        """
        Convert a ResumeResponse to ResumeData for template rendering.
        """
        return ResumeData(**response.model_dump(
            exclude={"id", "session_id", "created_at", "updated_at"}
        ))

    # =========================================================================
    # Sanitization
    # =========================================================================

    def _sanitize_resume_data(self, data: ResumeCreate) -> ResumeCreate:
        """Sanitize all text fields in a resume creation request."""
        sanitized = data.model_copy()

        # Sanitize personal info
        sanitized.first_name = sanitize_text(sanitized.first_name)
        sanitized.last_name = sanitize_text(sanitized.last_name)
        sanitized.professional_title = sanitize_text(sanitized.professional_title)
        sanitized.address = sanitize_text(sanitized.address)
        sanitized.nationality = sanitize_text(sanitized.nationality)

        # Sanitize URLs
        sanitized.linkedin = sanitize_url(sanitized.linkedin)
        sanitized.github = sanitize_url(sanitized.github)
        sanitized.portfolio = sanitize_url(sanitized.portfolio)
        sanitized.website = sanitize_url(sanitized.website)

        # Sanitize summary (allow basic HTML for formatting)
        sanitized.summary = sanitize_text(sanitized.summary, allow_html=True)

        return sanitized

    def _sanitize_resume_update(self, data: ResumeUpdate) -> ResumeUpdate:
        """Sanitize all text fields in a resume update request."""
        sanitized = data.model_copy()

        if sanitized.first_name is not None:
            sanitized.first_name = sanitize_text(sanitized.first_name)
        if sanitized.last_name is not None:
            sanitized.last_name = sanitize_text(sanitized.last_name)
        if sanitized.professional_title is not None:
            sanitized.professional_title = sanitize_text(
                sanitized.professional_title
            )
        if sanitized.summary is not None:
            sanitized.summary = sanitize_text(
                sanitized.summary, allow_html=True
            )
        if sanitized.linkedin is not None:
            sanitized.linkedin = sanitize_url(sanitized.linkedin)
        if sanitized.github is not None:
            sanitized.github = sanitize_url(sanitized.github)
        if sanitized.portfolio is not None:
            sanitized.portfolio = sanitize_url(sanitized.portfolio)
        if sanitized.website is not None:
            sanitized.website = sanitize_url(sanitized.website)

        return sanitized
