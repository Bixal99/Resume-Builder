# 🚀 Professional Resume Builder — Run Guide

## Prerequisites

- **Python 3.10+** installed ([python.org](https://www.python.org/downloads/))
- **pip** (comes with Python)

---

## Quick Start (3 Steps)

### Step 1: Create Virtual Environment

```bash
cd d:\My_products\Automated_CV_Generator

# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# OR (Windows CMD)
.\venv\Scripts\activate.bat

# OR (Linux/Mac)
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Optional — For PDF Download feature, install ONE of these:**

```bash
# Option A: WeasyPrint (simpler, recommended for local dev)
pip install weasyprint

# Option B: Playwright (pixel-perfect PDFs, heavier)
pip install playwright
playwright install chromium
```

> **Note:** The app runs perfectly without PDF engines — you can use the builder, fill forms, and see the live preview. PDF download will only fail if no engine is installed.

### Step 3: Run the Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Open in Browser

- **Landing Page:** http://127.0.0.1:8000
- **Resume Builder:** http://127.0.0.1:8000/builder
- **API Docs:** http://127.0.0.1:8000/docs

---

## What You Can Do

1. **Landing Page** → Premium landing page at `/`
2. **Builder** → Click "Build Your Resume" or go to `/builder`
3. **Fill Forms** → Step through: Personal Info → Summary → Experience → Education → Projects → Skills → Additional → Template → Review → Download
4. **Live Preview** → See your resume update in real-time on the right panel
5. **Auto-Save** → Your data is saved to browser localStorage automatically
6. **Download PDF** → On the Download step (requires WeasyPrint or Playwright)

---

## Project Structure

```
Automated_CV_Generator/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── core/
│   │   ├── config.py              # Settings
│   │   ├── database.py            # SQLite async engine
│   │   └── security.py            # Input sanitization
│   ├── models/                    # SQLAlchemy ORM models
│   ├── schemas/                   # Pydantic validation schemas
│   ├── repositories/              # Data access layer
│   ├── services/                  # Business logic and PDF
│   ├── api/
│   │   ├── routes.py              # REST API endpoints
│   │   ├── pages.py               # HTML page serving
│   │   └── deps.py                # Dependency injection
│   ├── templates/resume_templates/
│   │   ├── base.html              # Base Jinja2 template
│   │   └── modern/                # Modern Professional template
│   └── frontend/
│       ├── index.html             # Landing page
│       ├── builder.html           # Builder page
│       └── static/                # CSS and JS assets
├── requirements.txt
├── .env                           # Environment config
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/resumes` | Create resume |
| GET | `/api/resumes/{id}` | Get resume |
| PUT | `/api/resumes/{id}` | Update resume |
| DELETE | `/api/resumes/{id}` | Delete resume |
| POST | `/api/preview` | Render live preview HTML |
| POST | `/api/download/pdf` | Generate and download PDF |
| GET | `/api/templates` | List available templates |

---

## Troubleshooting

### "ModuleNotFoundError"
Make sure your virtual environment is activated and `pip install -r requirements.txt` completed successfully.

### "PDF generation failed"
Install a PDF engine: `pip install weasyprint` (simplest option).

### Port already in use
Use a different port: `uvicorn app.main:app --reload --port 8001`

### Database errors
Delete `data/resume_builder.db` and restart — tables are auto-created on startup.

---

## Summary of All Commands

```bash
# One-time setup
cd d:\My_products\Automated_CV_Generator
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install weasyprint          # Optional: for PDF export

# Run (every time)
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** in your browser!
