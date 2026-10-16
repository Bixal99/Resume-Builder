# =============================================================================
# Professional Resume Builder — Dockerfile
# =============================================================================
# Multi-stage build for production deployment with Playwright Chromium support
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install system dependencies required by WeasyPrint and Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    libcairo2 \
    # Playwright/Chromium shared libraries
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    # General utilities & fonts
    curl \
    fonts-liberation \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# --- Build Stage ---
FROM base AS builder
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# Install Playwright Chromium browser
RUN pip install playwright && python -m playwright install chromium

# --- Production Stage ---
FROM base AS production
WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local
COPY --from=builder /ms-playwright /ms-playwright
RUN chmod -R 777 /ms-playwright

# Copy application code
COPY . .

# Create necessary directories with open permissions
RUN mkdir -p data uploads exports && chmod -R 777 data uploads exports

# Expose port (Hugging Face default 7860; Render/Docker can override via PORT)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/api/health || exit 1

# Run the application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
