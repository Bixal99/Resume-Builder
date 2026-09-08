# =============================================================================
# Professional Resume Builder — Resume Pydantic Schemas
# =============================================================================
"""
Pydantic schemas for validating resume data in API requests and responses.

Schema hierarchy:
- *Base schemas define shared fields
- *Create schemas are used for POST requests
- *Update schemas allow partial updates (all fields optional)
- *Response schemas include id and timestamps

The ResumeData schema is the main "full resume" schema used for
live preview rendering and PDF generation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# =============================================================================
# Education Schemas
# =============================================================================

class EducationBase(BaseModel):
    """Shared education fields."""
    id: Optional[str] = None
    degree: Optional[str] = Field(None, max_length=200)
    field_of_study: Optional[str] = Field(None, max_length=200)
    institution: Optional[str] = Field(None, max_length=300)
    location: Optional[str] = Field(None, max_length=300)
    start_date: Optional[str] = Field(None, max_length=20)
    end_date: Optional[str] = Field(None, max_length=20)
    is_current: bool = False
    grade: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    sort_order: int = 0


class EducationCreate(EducationBase):
    """Schema for creating an education entry."""
    pass


class EducationResponse(EducationBase):
    """Schema for education API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Experience Schemas
# =============================================================================

class ExperienceBase(BaseModel):
    """Shared experience fields."""
    id: Optional[str] = None
    company: Optional[str] = Field(None, max_length=300)
    position: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=300)
    start_date: Optional[str] = Field(None, max_length=20)
    end_date: Optional[str] = Field(None, max_length=20)
    is_current: bool = False
    description: Optional[str] = None
    achievements: Optional[list[str]] = Field(default_factory=list)
    sort_order: int = 0

    @field_validator("achievements", mode="before")
    @classmethod
    def parse_achievements(cls, v):
        """Accept both JSON string and list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [v] if v else []
        return v or []


class ExperienceCreate(ExperienceBase):
    """Schema for creating an experience entry."""
    pass


class ExperienceResponse(ExperienceBase):
    """Schema for experience API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Project Schemas
# =============================================================================

class ProjectBase(BaseModel):
    """Shared project fields."""
    id: Optional[str] = None
    title: Optional[str] = Field(None, max_length=300)
    date: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    technologies: Optional[list[str]] = Field(default_factory=list)
    github_url: Optional[str] = Field(None, max_length=500)
    live_url: Optional[str] = Field(None, max_length=500)
    highlights: Optional[list[str]] = Field(default_factory=list)
    sort_order: int = 0

    @field_validator("technologies", "highlights", mode="before")
    @classmethod
    def parse_list_field(cls, v):
        """Accept both JSON string and list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [v] if v else []
        return v or []


class ProjectCreate(ProjectBase):
    """Schema for creating a project entry."""
    pass


class ProjectResponse(ProjectBase):
    """Schema for project API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Skill Schemas
# =============================================================================

class SkillBase(BaseModel):
    """Shared skill fields."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field("technical", max_length=50)
    proficiency: Optional[int] = Field(None, ge=1, le=5)
    sort_order: int = 0


class SkillCreate(SkillBase):
    """Schema for creating a skill entry."""
    pass


class SkillResponse(SkillBase):
    """Schema for skill API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Language Schemas
# =============================================================================

class LanguageBase(BaseModel):
    """Shared language fields."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    fluency: Optional[str] = Field(None, max_length=50)
    sort_order: int = 0


class LanguageCreate(LanguageBase):
    """Schema for creating a language entry."""
    pass


class LanguageResponse(LanguageBase):
    """Schema for language API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Certification Schemas
# =============================================================================

class CertificationBase(BaseModel):
    """Shared certification fields."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=300)
    issuer: Optional[str] = Field(None, max_length=300)
    date: Optional[str] = Field(None, max_length=20)
    expiry_date: Optional[str] = Field(None, max_length=20)
    credential_id: Optional[str] = Field(None, max_length=200)
    credential_url: Optional[str] = Field(None, max_length=500)
    sort_order: int = 0


class CertificationCreate(CertificationBase):
    """Schema for creating a certification entry."""
    pass


class CertificationResponse(CertificationBase):
    """Schema for certification API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Award Schemas
# =============================================================================

class AwardBase(BaseModel):
    """Shared award fields."""
    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=300)
    issuer: Optional[str] = Field(None, max_length=300)
    date: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    sort_order: int = 0


class AwardCreate(AwardBase):
    """Schema for creating an award entry."""
    pass


class AwardResponse(AwardBase):
    """Schema for award API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Volunteer Experience Schemas
# =============================================================================

class VolunteerBase(BaseModel):
    """Shared volunteer experience fields."""
    id: Optional[str] = None
    organization: Optional[str] = Field(None, max_length=300)
    role: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=300)
    start_date: Optional[str] = Field(None, max_length=20)
    end_date: Optional[str] = Field(None, max_length=20)
    is_current: bool = False
    description: Optional[str] = None
    sort_order: int = 0


class VolunteerCreate(VolunteerBase):
    """Schema for creating a volunteer entry."""
    pass


class VolunteerResponse(VolunteerBase):
    """Schema for volunteer API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Reference Schemas
# =============================================================================

class ReferenceBase(BaseModel):
    """Shared reference fields."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    title: Optional[str] = Field(None, max_length=200)
    company: Optional[str] = Field(None, max_length=300)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    relationship_type: Optional[str] = Field(None, max_length=100)
    sort_order: int = 0


class ReferenceCreate(ReferenceBase):
    """Schema for creating a reference entry."""
    pass


class ReferenceResponse(ReferenceBase):
    """Schema for reference API responses."""
    model_config = ConfigDict(from_attributes=True)
    id: str


# =============================================================================
# Resume Schemas
# =============================================================================

class ResumeBase(BaseModel):
    """Shared resume fields."""
    title: str = Field("Untitled Resume", max_length=255)
    template_id: str = Field("modern", max_length=100)
    page_size: str = Field("A4", max_length=10)
    section_order: Optional[list[str]] = Field(default_factory=list)
    hidden_sections: Optional[list[str]] = Field(default_factory=list)
    theme_settings: Optional[dict] = Field(default_factory=dict)

    # Personal information
    photo: Optional[str] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    professional_title: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    linkedin: Optional[str] = Field(None, max_length=500)
    github: Optional[str] = Field(None, max_length=500)
    portfolio: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=500)
    nationality: Optional[str] = Field(None, max_length=100)

    # Professional summary
    summary: Optional[str] = None


class ResumeCreate(ResumeBase):
    """Schema for creating a new resume (POST body)."""
    session_id: Optional[str] = None
    education: list[EducationCreate] = Field(default_factory=list)
    experience: list[ExperienceCreate] = Field(default_factory=list)
    projects: list[ProjectCreate] = Field(default_factory=list)
    skills: list[SkillCreate] = Field(default_factory=list)
    languages: list[LanguageCreate] = Field(default_factory=list)
    certifications: list[CertificationCreate] = Field(default_factory=list)
    awards: list[AwardCreate] = Field(default_factory=list)
    volunteer: list[VolunteerCreate] = Field(default_factory=list)
    references: list[ReferenceCreate] = Field(default_factory=list)


class ResumeUpdate(BaseModel):
    """
    Schema for updating a resume (PUT/PATCH body).

    All fields are optional to support partial updates.
    """
    title: Optional[str] = Field(None, max_length=255)
    template_id: Optional[str] = Field(None, max_length=100)
    page_size: Optional[str] = Field(None, max_length=10)
    section_order: Optional[list[str]] = None
    hidden_sections: Optional[list[str]] = None

    photo: Optional[str] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    professional_title: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    linkedin: Optional[str] = Field(None, max_length=500)
    github: Optional[str] = Field(None, max_length=500)
    portfolio: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=500)
    nationality: Optional[str] = Field(None, max_length=100)
    summary: Optional[str] = None

    education: Optional[list[EducationCreate]] = None
    experience: Optional[list[ExperienceCreate]] = None
    projects: Optional[list[ProjectCreate]] = None
    skills: Optional[list[SkillCreate]] = None
    languages: Optional[list[LanguageCreate]] = None
    certifications: Optional[list[CertificationCreate]] = None
    awards: Optional[list[AwardCreate]] = None
    volunteer: Optional[list[VolunteerCreate]] = None
    references: Optional[list[ReferenceCreate]] = None


class ResumeResponse(ResumeBase):
    """Full resume response including all sections."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    education: list[EducationResponse] = Field(default_factory=list)
    experience: list[ExperienceResponse] = Field(default_factory=list)
    projects: list[ProjectResponse] = Field(default_factory=list)
    skills: list[SkillResponse] = Field(default_factory=list)
    languages: list[LanguageResponse] = Field(default_factory=list)
    certifications: list[CertificationResponse] = Field(default_factory=list)
    awards: list[AwardResponse] = Field(default_factory=list)
    volunteer: list[VolunteerResponse] = Field(default_factory=list)
    references: list[ReferenceResponse] = Field(default_factory=list)


# =============================================================================
# Resume Data — Used for template rendering and PDF generation
# =============================================================================

class ResumeData(BaseModel):
    """
    The complete resume data contract used by template engine and PDF engine.

    This is the schema that Jinja2 templates and the preview endpoint consume.
    It mirrors ResumeResponse but is designed to be constructed from either
    the database or from raw JSON (localStorage auto-save).
    """
    # Personal
    photo: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    professional_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    nationality: Optional[str] = None

    # Summary
    summary: Optional[str] = None

    # Template settings
    template_id: str = "modern"
    page_size: str = "A4"
    section_order: list[str] = Field(default_factory=list)
    hidden_sections: list[str] = Field(default_factory=list)
    theme_settings: dict = Field(default_factory=dict)

    # Sections
    education: list[EducationCreate] = Field(default_factory=list)
    experience: list[ExperienceCreate] = Field(default_factory=list)
    projects: list[ProjectCreate] = Field(default_factory=list)
    skills: list[SkillCreate] = Field(default_factory=list)
    languages: list[LanguageCreate] = Field(default_factory=list)
    certifications: list[CertificationCreate] = Field(default_factory=list)
    awards: list[AwardCreate] = Field(default_factory=list)
    volunteer: list[VolunteerCreate] = Field(default_factory=list)
    references: list[ReferenceCreate] = Field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Combine first and last name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or ""

    @property
    def has_contact_info(self) -> bool:
        """Check if any contact information is provided."""
        return any([
            self.email, self.phone, self.address,
            self.linkedin, self.github, self.portfolio, self.website,
        ])

    @property
    def has_personal_info(self) -> bool:
        """Check if basic personal info is provided."""
        return bool(self.first_name or self.last_name)

    def has_section(self, section: str) -> bool:
        """Check if a section has any entries."""
        data = getattr(self, section, None)
        if isinstance(data, list):
            return len(data) > 0
        if isinstance(data, str):
            return bool(data.strip())
        return data is not None


# =============================================================================
# Template Info Schema
# =============================================================================

class TemplateInfo(BaseModel):
    """Information about an available resume template."""
    id: str
    name: str
    description: str
    thumbnail: Optional[str] = None
    is_premium: bool = False
    category: str = "professional"  # professional, creative, minimal, academic
