# =============================================================================
# Professional Resume Builder — Page Routes
# =============================================================================
"""
HTML page-serving routes.

Serves the frontend HTML pages (landing page, builder, etc.)
using FastAPI's FileResponse.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import settings

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve the landing page."""
    index_path = settings.frontend_dir / "index.html"
    return FileResponse(
        path=str(index_path),
        media_type="text/html",
    )


@router.get("/builder", response_class=HTMLResponse)
async def builder_page():
    """Serve the resume builder page."""
    builder_path = settings.frontend_dir / "builder.html"
    return FileResponse(
        path=str(builder_path),
        media_type="text/html",
    )
