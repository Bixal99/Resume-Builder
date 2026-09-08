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

# Install system dependencies required by WeasyPrint and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    # Playwright/Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    libglib2.0-0 \
    libuuid1 \
    # General utilities
    curl \
    fonts-liberation \
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

# Create necessary directories and set Hugging Face compatible user permissions
RUN mkdir -p data uploads exports && chmod -R 777 data uploads exports /app

# Set up a non-root user (Hugging Face Spaces runs as uid 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
