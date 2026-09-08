# =============================================================================
# Professional Resume Builder — FastAPI Application Entry Point
# =============================================================================
"""
Main application module.

Creates the FastAPI app with:
- CORS middleware
- Static file serving
- API and page routes
- Database lifecycle (init on startup, close on shutdown)
- Global exception handlers
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import close_db, init_db
from app.api.routes import router as api_router
from app.api.pages import router as pages_router

# --- Logging ---
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.

    On startup: Initialize database tables.
    On shutdown: Close database connections.
    """
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Ensure directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.export_dir).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    await close_db()
    logger.info("Application shutdown complete")


# =============================================================================
# Create FastAPI Application
# =============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A professional resume builder with live preview and PDF export.",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# =============================================================================
# Middleware
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Static Files
# =============================================================================

# Serve frontend static assets (CSS, JS, images, fonts)
static_dir = settings.static_dir
if static_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(static_dir)),
        name="static",
    )

# Serve uploaded files (photos)
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=str(upload_dir)),
    name="uploads",
)


# =============================================================================
# Routes
# =============================================================================

# API routes (/api/*)
app.include_router(api_router)

# Page routes (/, /builder)
app.include_router(pages_router)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler — return JSON for API, redirect for pages."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Resource not found"},
        )
    # For page requests, serve the landing page (SPA-style fallback)
    from fastapi.responses import FileResponse
    index_path = settings.frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), status_code=200)
    return JSONResponse(status_code=404, content={"detail": "Page not found"})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Custom 500 handler with logging."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
