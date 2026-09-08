# =============================================================================
# Professional Resume Builder — Dependency Injection
# =============================================================================
"""
FastAPI dependency injection providers.

These functions are used with FastAPI's `Depends()` to inject
services and sessions into route handlers.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.resume_service import ResumeService
from app.services.template_service import template_service
from app.services.pdf_service import pdf_service


async def get_resume_service(
    session: AsyncSession = Depends(get_db_session),
) -> ResumeService:
    """
    Provide a ResumeService instance with a database session.

    Usage:
        @router.get("/resumes")
        async def list_resumes(
            service: ResumeService = Depends(get_resume_service)
        ):
            ...
    """
    return ResumeService(session)


def get_template_service():
    """Provide the singleton TemplateService instance."""
    return template_service


def get_pdf_service():
    """Provide the singleton PDFService instance."""
    return pdf_service

