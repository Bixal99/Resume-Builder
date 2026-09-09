# =============================================================================
# Professional Resume Builder — REST API Routes
# =============================================================================
"""
REST API endpoints for resume CRUD, preview rendering, and PDF generation.

All routes are prefixed with /api/ and return JSON responses
(except preview and PDF download which return HTML/binary).
"""

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse

from app.api.deps import get_pdf_service, get_resume_service, get_template_service
from app.schemas.resume import (
    ResumeCreate,
    ResumeData,
    ResumeResponse,
    ResumeUpdate,
    TemplateInfo,
)
from typing import Optional
from pydantic import BaseModel
from app.services.pdf_service import PDFService
from app.services.resume_service import ResumeService
from app.services.template_service import TemplateService
from app.services.parser import (
    extract_text_from_pdf,
    extract_profile_photo_from_pdf,
    parse_resume_with_llm,
    stream_parse_resume_with_llm,
    optimize_bullet_with_llm,
)

import asyncio
import io
import json
import logging
import queue
import re
import threading

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and Docker healthcheck."""
    return {"status": "healthy", "version": "1.0.0"}


# =============================================================================
# Resume CRUD
# =============================================================================

@router.post("/resumes", response_model=ResumeResponse, status_code=201)
async def create_resume(
    data: ResumeCreate,
    service: ResumeService = Depends(get_resume_service),
):
    """Create a new resume."""
    return await service.create_resume(data)


@router.get("/resumes/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: str,
    service: ResumeService = Depends(get_resume_service),
):
    """Fetch a resume by ID."""
    resume = await service.get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.get("/resumes/session/{session_id}", response_model=ResumeResponse)
async def get_resume_by_session(
    session_id: str,
    service: ResumeService = Depends(get_resume_service),
):
    """Fetch the latest resume for an anonymous session."""
    resume = await service.get_resume_by_session(session_id)
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found for this session")
    return resume


@router.put("/resumes/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: str,
    data: ResumeUpdate,
    service: ResumeService = Depends(get_resume_service),
):
    """Update an existing resume (full or partial)."""
    resume = await service.update_resume(resume_id, data)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.delete("/resumes/{resume_id}")
async def delete_resume(
    resume_id: str,
    service: ResumeService = Depends(get_resume_service),
):
    """Delete a resume and all its sections."""
    deleted = await service.delete_resume(resume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"detail": "Resume deleted successfully"}


# =============================================================================
# Preview — Render resume HTML from raw data (no DB required)
# =============================================================================

@router.post("/preview", response_class=HTMLResponse)
async def render_preview(
    data: ResumeData,
    template_svc: TemplateService = Depends(get_template_service),
):
    """
    Render a live preview of the resume.

    Accepts the full resume data and returns rendered HTML.
    This endpoint is called by the frontend on every form change
    (debounced) to update the live preview.
    """
    html = template_svc.render_resume(data)
    return HTMLResponse(content=html)


# =============================================================================
# PDF Download
# =============================================================================

@router.post("/download/pdf")
async def download_pdf(
    data: ResumeData,
    pdf_svc: PDFService = Depends(get_pdf_service),
):
    """
    Generate and download a PDF resume.

    Accepts the full resume data, renders it via the template engine,
    then generates a PDF using Playwright or WeasyPrint.
    """
    try:
        pdf_bytes = await pdf_svc.generate_pdf(data)
    except Exception as e:
        logger.exception("PDF generation error in /download/pdf")
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(e)}"
        )

    if not pdf_bytes or len(pdf_bytes) == 0:
        logger.error("PDF generation produced zero bytes")
        raise HTTPException(status_code=500, detail="PDF generation returned empty output")

    # Build safe filename from name (sanitizing special characters)
    name_parts = [data.first_name, data.last_name]
    raw_name = "_".join(p.strip() for p in name_parts if p and p.strip()) or "resume"
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_name)
    filename = f"{safe_name}_resume.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


# =============================================================================
# Resume Parsing / Import
# =============================================================================

@router.post("/parse", response_model=ResumeData)
async def parse_resume_upload(file: UploadFile = File(...)):
    """
    Extract text and parse structured resume data from an uploaded PDF.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files (.pdf) are supported for resume parsing."
        )

    try:
        content = await file.read()
        if not content or len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        text = await asyncio.to_thread(extract_text_from_pdf, content)
        photo = await asyncio.to_thread(extract_profile_photo_from_pdf, content)
        parsed_data = await asyncio.to_thread(parse_resume_with_llm, text, photo=photo)
        return parsed_data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error parsing resume PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse resume: {str(e)}"
        )


@router.post("/parse-stream")
async def parse_resume_upload_stream(file: UploadFile = File(...)):
    """
    Extract text and stream real-time progress events and tokens for resume parsing.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files (.pdf) are supported for resume parsing."
        )

    content = await file.read()
    if not content or len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = await asyncio.to_thread(extract_text_from_pdf, content)
        photo = await asyncio.to_thread(extract_profile_photo_from_pdf, content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {str(e)}")

    async def event_generator():
        q = queue.Queue()

        def worker():
            try:
                for item in stream_parse_resume_with_llm(text, photo=photo):
                    q.put(item)
            except Exception as err:
                q.put({"event": "error", "stage": 0, "detail": str(err), "pct": 0})
            finally:
                q.put(None)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            try:
                item = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.04)
                continue

            if item is None:
                break

            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


class BulletOptimizeRequest(BaseModel):
    bullet: str
    role: Optional[str] = ""
    company: Optional[str] = ""
    mode: Optional[str] = "star"


@router.post("/ai/optimize-bullet")
async def optimize_bullet_endpoint(req: BulletOptimizeRequest):
    """
    AI-driven STAR method bullet point optimizer with quantifiable metrics.
    """
    if not req.bullet or not req.bullet.strip():
        raise HTTPException(status_code=400, detail="Bullet point text cannot be empty.")

    try:
        res = await asyncio.to_thread(
            optimize_bullet_with_llm,
            bullet=req.bullet.strip(),
            role=req.role or "",
            company=req.company or "",
            mode=req.mode or "star"
        )
        return res
    except Exception as e:
        logger.exception(f"Error optimizing bullet point: {e}")
        raise HTTPException(status_code=500, detail=f"AI optimization failed: {str(e)}")


@router.post("/page-count")
async def get_page_count(
    data: ResumeData,
    pdf_svc: PDFService = Depends(get_pdf_service),
):
    """
    Count the number of pages in the generated PDF.

    Uses the same PDF engine as /download/pdf so the page count
    is guaranteed to match the actual downloaded file.
    """
    import re

    pdf_bytes = await pdf_svc.generate_pdf(data)
    # Parse PDF byte stream for page count.
    # The Pages dictionary contains /Count N which is the total page count.
    text = pdf_bytes.decode("latin-1")
    match = re.search(r"/Type\s*/Pages.*?/Count\s+(\d+)", text, re.DOTALL)
    if match:
        pages = int(match.group(1))
    else:
        # Fallback: count /Type /Page entries (not /Pages)
        pages = len(re.findall(r"/Type\s*/Page\b(?!s)", text))
    return {"pages": max(1, pages)}


# =============================================================================
# Templates
# =============================================================================

@router.get("/templates", response_model=list[TemplateInfo])
async def list_templates(
    template_svc: TemplateService = Depends(get_template_service),
):
    """List all available resume templates."""
    return template_svc.get_available_templates()


@router.get("/templates/{template_id}", response_model=TemplateInfo)
async def get_template(
    template_id: str,
    template_svc: TemplateService = Depends(get_template_service),
):
    """Get information about a specific template."""
    info = template_svc.get_template_info(template_id)
    if not info:
        raise HTTPException(status_code=404, detail="Template not found")
    return info
