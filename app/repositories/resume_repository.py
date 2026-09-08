# =============================================================================
# Professional Resume Builder — Resume Repository
# =============================================================================
"""
Data access layer for resume CRUD operations.

Handles all database interactions for resumes and their child sections.
The repository uses SQLAlchemy async sessions and follows the repository
pattern to keep database logic separate from business logic.
"""

import json
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resume import (
    Award,
    Certification,
    Education,
    Experience,
    Language,
    Project,
    Reference,
    Resume,
    Skill,
    VolunteerExperience,
)
from app.schemas.resume import ResumeCreate, ResumeUpdate


class ResumeRepository:
    """
    Repository for resume database operations.

    All methods accept an AsyncSession and return ORM model instances.
    The service layer is responsible for converting to/from Pydantic schemas.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get_by_id(self, resume_id: str) -> Optional[Resume]:
        """
        Fetch a resume by ID with all related sections eagerly loaded.
        """
        stmt = (
            select(Resume)
            .options(
                selectinload(Resume.education),
                selectinload(Resume.experience),
                selectinload(Resume.projects),
                selectinload(Resume.skills),
                selectinload(Resume.languages),
                selectinload(Resume.certifications),
                selectinload(Resume.awards),
                selectinload(Resume.volunteer),
                selectinload(Resume.references),
            )
            .where(Resume.id == resume_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_session_id(self, session_id: str) -> Optional[Resume]:
        """
        Fetch the most recent resume for a session (anonymous user).
        """
        stmt = (
            select(Resume)
            .options(
                selectinload(Resume.education),
                selectinload(Resume.experience),
                selectinload(Resume.projects),
                selectinload(Resume.skills),
                selectinload(Resume.languages),
                selectinload(Resume.certifications),
                selectinload(Resume.awards),
                selectinload(Resume.volunteer),
                selectinload(Resume.references),
            )
            .where(Resume.session_id == session_id)
            .order_by(Resume.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_user(self, user_id: str) -> list[Resume]:
        """
        List all resumes for a user, ordered by last update.
        """
        stmt = (
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # Create Operations
    # =========================================================================

    async def create(self, data: ResumeCreate) -> Resume:
        """
        Create a new resume with all sections.

        Accepts a ResumeCreate schema and creates the resume along with
        all child section entries in a single transaction.
        """
        # Create the resume (exclude section lists — handled separately)
        resume_data = data.model_dump(exclude={
            "education", "experience", "projects", "skills",
            "languages", "certifications", "awards", "volunteer", "references",
        })
        if isinstance(resume_data.get("section_order"), list):
            resume_data["section_order"] = json.dumps(resume_data["section_order"])
        if isinstance(resume_data.get("hidden_sections"), list):
            resume_data["hidden_sections"] = json.dumps(resume_data["hidden_sections"])
        if isinstance(resume_data.get("theme_settings"), (dict, list)):
            resume_data["theme_settings"] = json.dumps(resume_data["theme_settings"])

        valid_resume_cols = {c.name for c in Resume.__table__.columns}
        resume_data = {k: v for k, v in resume_data.items() if k in valid_resume_cols}
        resume = Resume(**resume_data)
        self.db.add(resume)
        await self.db.flush()  # Get the resume.id

        # Create child sections
        await self._create_sections(resume, data)

        await self.db.flush()
        return await self.get_by_id(resume.id)

    async def _create_sections(self, resume: Resume, data: ResumeCreate) -> None:
        """Create all child section entries for a resume."""
        section_map = {
            "education": (data.education, Education),
            "experience": (data.experience, Experience),
            "projects": (data.projects, Project),
            "skills": (data.skills, Skill),
            "languages": (data.languages, Language),
            "certifications": (data.certifications, Certification),
            "awards": (data.awards, Award),
            "volunteer": (data.volunteer, VolunteerExperience),
            "references": (data.references, Reference),
        }

        for section_name, (items, model_class) in section_map.items():
            valid_cols = {c.name for c in model_class.__table__.columns}
            for i, item in enumerate(items):
                item_data = item.model_dump()
                item_data["resume_id"] = resume.id
                item_data["sort_order"] = i

                # Convert list fields to JSON strings for storage
                for field_name in ("achievements", "technologies", "highlights"):
                    if field_name in item_data and isinstance(item_data[field_name], list):
                        item_data[field_name] = json.dumps(item_data[field_name])

                # Remove any client-supplied ID so the database generates a fresh, unique UUID
                item_data.pop("id", None)

                # Filter down to valid model column attributes
                item_data = {k: v for k, v in item_data.items() if k in valid_cols}

                entry = model_class(**item_data)
                self.db.add(entry)

    # =========================================================================
    # Update Operations
    # =========================================================================

    async def update(self, resume_id: str, data: ResumeUpdate) -> Optional[Resume]:
        """
        Update a resume and optionally replace its sections.

        For section lists (education, experience, etc.), the update strategy is
        "replace all" — existing entries are deleted and new ones are created.
        This simplifies handling of add/remove/reorder operations.
        """
        resume = await self.get_by_id(resume_id)
        if not resume:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Separate scalar fields from section lists
        section_keys = {
            "education", "experience", "projects", "skills",
            "languages", "certifications", "awards", "volunteer", "references",
        }
        scalar_data = {k: v for k, v in update_data.items() if k not in section_keys}
        if "section_order" in scalar_data and isinstance(scalar_data["section_order"], list):
            scalar_data["section_order"] = json.dumps(scalar_data["section_order"])
        if "hidden_sections" in scalar_data and isinstance(scalar_data["hidden_sections"], list):
            scalar_data["hidden_sections"] = json.dumps(scalar_data["hidden_sections"])
        if "theme_settings" in scalar_data and isinstance(scalar_data["theme_settings"], (dict, list)):
            scalar_data["theme_settings"] = json.dumps(scalar_data["theme_settings"])

        valid_resume_cols = {c.name for c in Resume.__table__.columns}
        scalar_data = {k: v for k, v in scalar_data.items() if k in valid_resume_cols}
        section_data = {k: v for k, v in update_data.items() if k in section_keys}

        # Update scalar fields
        for key, value in scalar_data.items():
            setattr(resume, key, value)

        # Replace sections (delete old, create new)
        if section_data:
            await self._replace_sections(resume, section_data)

        await self.db.flush()
        self.db.expire_all()
        return await self.get_by_id(resume_id)

    async def _replace_sections(
        self, resume: Resume, section_data: dict
    ) -> None:
        """
        Replace section entries using delete-and-recreate strategy.
        """
        section_model_map = {
            "education": Education,
            "experience": Experience,
            "projects": Project,
            "skills": Skill,
            "languages": Language,
            "certifications": Certification,
            "awards": Award,
            "volunteer": VolunteerExperience,
            "references": Reference,
        }

        for section_name, items in section_data.items():
            if items is None:
                continue

            model_class = section_model_map[section_name]

            # Delete existing entries for this section
            await self.db.execute(
                delete(model_class).where(model_class.resume_id == resume.id)
            )

            valid_cols = {c.name for c in model_class.__table__.columns}
            # Create new entries
            for i, item_data in enumerate(items):
                if isinstance(item_data, dict):
                    entry_data = dict(item_data)
                else:
                    entry_data = item_data.model_dump() if hasattr(item_data, 'model_dump') else dict(item_data)

                entry_data["resume_id"] = resume.id
                entry_data["sort_order"] = i

                # Convert list fields to JSON strings
                for field_name in ("achievements", "technologies", "highlights"):
                    if field_name in entry_data and isinstance(entry_data[field_name], list):
                        entry_data[field_name] = json.dumps(entry_data[field_name])

                # Remove any client-supplied ID so the database generates a fresh, unique UUID
                entry_data.pop("id", None)

                # Filter down to valid model column attributes
                entry_data = {k: v for k, v in entry_data.items() if k in valid_cols}

                entry = model_class(**entry_data)
                self.db.add(entry)

    # =========================================================================
    # Delete Operations
    # =========================================================================

    async def delete(self, resume_id: str) -> bool:
        """
        Delete a resume and all its sections (cascaded).

        Returns True if the resume existed and was deleted.
        """
        resume = await self.get_by_id(resume_id)
        if not resume:
            return False

        await self.db.delete(resume)
        await self.db.flush()
        return True
