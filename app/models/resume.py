# =============================================================================
# Professional Resume Builder — Resume Models
# =============================================================================
"""
SQLAlchemy models for the resume and all its sections.

Normalized schema design:
- Resume (parent) has one-to-many relationships to each section
- Each section has a `sort_order` for drag-and-drop reordering
- All models inherit UUID PK and timestamps from Base

The schema supports multiple resumes per user and is designed for
future extensibility (AI scoring, analytics, sharing, etc.).
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Resume(Base):
    """
    Root resume model — the top-level container for all resume data.

    Each resume belongs to one user (optional) and contains multiple
    sections as child relationships.
    """

    __tablename__ = "resumes"

    # --- Ownership ---
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    # Session-based identifier for anonymous users (from localStorage)
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    # --- Resume Metadata ---
    title: Mapped[str] = mapped_column(
        String(255), default="Untitled Resume", nullable=False
    )
    template_id: Mapped[str] = mapped_column(
        String(100), default="modern", nullable=False
    )
    page_size: Mapped[str] = mapped_column(
        String(10), default="A4", nullable=False
    )  # A4 or Letter
    section_order: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hidden_sections: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    theme_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Personal Information ---
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Base64 data URI
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    professional_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linkedin: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    portfolio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # --- Professional Summary ---
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="resumes"
    )
    education: Mapped[list["Education"]] = relationship(
        "Education",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Education.sort_order",
    )
    experience: Mapped[list["Experience"]] = relationship(
        "Experience",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Experience.sort_order",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Project.sort_order",
    )
    skills: Mapped[list["Skill"]] = relationship(
        "Skill",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Skill.sort_order",
    )
    languages: Mapped[list["Language"]] = relationship(
        "Language",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Language.sort_order",
    )
    certifications: Mapped[list["Certification"]] = relationship(
        "Certification",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Certification.sort_order",
    )
    awards: Mapped[list["Award"]] = relationship(
        "Award",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Award.sort_order",
    )
    volunteer: Mapped[list["VolunteerExperience"]] = relationship(
        "VolunteerExperience",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="VolunteerExperience.sort_order",
    )
    references: Mapped[list["Reference"]] = relationship(
        "Reference",
        back_populates="resume",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Reference.sort_order",
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id!r}, title={self.title!r})>"


# =============================================================================
# Section Models — Each section is a child of Resume
# =============================================================================


class Education(Base):
    """Education entry (degree, institution, dates, etc.)."""

    __tablename__ = "education"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    degree: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    field_of_study: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    institution: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="education")


class Experience(Base):
    """Work experience entry with achievements/responsibilities."""

    __tablename__ = "experience"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    company: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Achievements stored as JSON array string for simplicity
    achievements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="experience")


class Project(Base):
    """Project entry with technologies and links."""

    __tablename__ = "projects"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Technologies stored as JSON array string
    technologies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    live_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Highlights stored as JSON array string
    highlights: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="projects")


class Skill(Base):
    """Skill entry with category and proficiency."""

    __tablename__ = "skills"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(
        String(50), default="technical", nullable=True
    )  # technical, soft, language, framework, tool
    proficiency: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1-5 scale (optional)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="skills")


class Language(Base):
    """Language proficiency entry."""

    __tablename__ = "languages"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    fluency: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # native, fluent, advanced, intermediate, beginner

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="languages")


class Certification(Base):
    """Professional certification entry."""

    __tablename__ = "certifications"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    expiry_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    credential_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    credential_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="certifications")


class Award(Base):
    """Award or honor entry."""

    __tablename__ = "awards"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="awards")


class VolunteerExperience(Base):
    """Volunteer experience entry."""

    __tablename__ = "volunteer_experience"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    organization: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="volunteer")


class Reference(Base):
    """Professional reference entry (optional, hidden if empty)."""

    __tablename__ = "references"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    relationship_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "Former Manager", "Colleague"

    # --- Relationships ---
    resume: Mapped["Resume"] = relationship("Resume", back_populates="references")
