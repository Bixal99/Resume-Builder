# =============================================================================
# Professional Resume Builder — Application Configuration
# =============================================================================
"""
Centralized configuration via Pydantic BaseSettings.

All settings are loaded from environment variables with sensible defaults.
Use a .env file for local development (see .env.example).
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes are grouped by concern: app, database, security, PDF, storage.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "Professional Resume Builder"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # ---- Database ----
    database_url: str = "sqlite+aiosqlite:///./data/resume_builder.db"

    # ---- Security ----
    secret_key: str = "change-this-to-a-random-secret-key-in-production"
    allowed_origins: str = "http://localhost:8000,http://localhost:3000"

    # ---- PDF Engine ----
    # "playwright" (primary, pixel-perfect) or "weasyprint" (lightweight fallback)
    pdf_engine: str = "playwright"

    # ---- Storage ----
    upload_dir: str = "./uploads"
    export_dir: str = "./exports"
    max_upload_size_mb: int = 5

    # ---- Future Auth ----
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ---- AI & Parsing ----
    hf_token: Optional[str] = None
    huggingface_token: Optional[str] = None

    # ---- Computed Properties ----

    @property
    def base_dir(self) -> Path:
        """Project root directory."""
        return Path(__file__).resolve().parent.parent.parent

    @property
    def templates_dir(self) -> Path:
        """Jinja2 templates directory."""
        return Path(__file__).resolve().parent.parent / "templates"

    @property
    def resume_templates_dir(self) -> Path:
        """Resume template directory containing all template themes."""
        return self.templates_dir / "resume_templates"

    @property
    def frontend_dir(self) -> Path:
        """Frontend HTML/CSS/JS directory."""
        return Path(__file__).resolve().parent.parent / "frontend"

    @property
    def static_dir(self) -> Path:
        """Static assets directory."""
        return self.frontend_dir / "static"

    @property
    def upload_path(self) -> Path:
        """Resolved upload directory path."""
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def export_path(self) -> Path:
        """Resolved export directory path."""
        path = Path(self.export_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


# Singleton settings instance — import this throughout the app
settings = Settings()
