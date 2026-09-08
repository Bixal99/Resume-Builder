# =============================================================================
# Professional Resume Builder — PDF Generation Service
# =============================================================================
"""
PDF generation engine with Playwright (primary) and WeasyPrint (fallback).

The service renders resume HTML (from the template service) to a
professionally formatted PDF with proper page sizing, margins, and fonts.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.schemas.resume import ResumeData
from app.services.template_service import template_service

logger = logging.getLogger(__name__)

# Page dimensions in CSS units
PAGE_SIZES = {
    "A4": {"width": "210mm", "height": "297mm"},
    "Letter": {"width": "8.5in", "height": "11in"},
}


class PDFService:
    """
    Service for generating PDF resumes.

    Supports two engines:
    - **Playwright**: Uses headless Chromium for pixel-perfect rendering.
      Best quality, but requires Chromium to be installed.
    - **WeasyPrint**: Pure Python PDF rendering. Good quality, lighter weight.
      Used as a fallback if Playwright is unavailable.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None

    async def generate_pdf(
        self,
        data: ResumeData,
        template_id: Optional[str] = None,
    ) -> bytes:
        """
        Generate a PDF from resume data.

        Args:
            data: Complete resume data.
            template_id: Override template (defaults to data.template_id).

        Returns:
            PDF file content as bytes.
        """
        # Render HTML from template
        html = template_service.render_resume(data, template_id)

        # Generate PDF using configured engine with reciprocal fallback
        engine = settings.pdf_engine.lower()

        if engine == "weasyprint":
            try:
                return self._generate_with_weasyprint(html, data.page_size)
            except Exception as e:
                logger.warning(
                    f"WeasyPrint PDF generation failed: {e}. "
                    f"Falling back to Playwright."
                )
                return await self._generate_with_playwright(html, data.page_size)
        else:
            try:
                return await self._generate_with_playwright(html, data.page_size)
            except Exception as e:
                logger.warning(
                    f"Playwright PDF generation failed: {e}. "
                    f"Attempting WeasyPrint fallback."
                )
                try:
                    return self._generate_with_weasyprint(html, data.page_size)
                except Exception as we:
                    logger.error(f"WeasyPrint fallback also failed: {we}")
                    raise RuntimeError(
                        f"PDF generation failed across both Playwright and WeasyPrint engines. "
                        f"Playwright error: {e}; WeasyPrint error: {we}"
                    ) from e

    async def _generate_with_playwright(
        self, html: str, page_size: str = "A4"
    ) -> bytes:
        """
        Generate PDF using Playwright with an automatic launch cascade:
        1. Default packaged Chromium
        2. Installed Google Chrome channel
        3. Installed Microsoft Edge channel
        4. Standard system binary executable paths
        """
        from starlette.concurrency import run_in_threadpool

        def _sync_generate() -> bytes:
            import os
            from playwright.sync_api import sync_playwright

            launch_args = [
                "--disable-gpu",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--font-render-hinting=medium",
            ]

            # Standard executable locations to check on Windows/Linux/Mac
            candidate_executables = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]

            with sync_playwright() as p:
                browser = None
                launch_errors = []

                # Cascade strategy:
                # 1. Default Playwright Chromium
                try:
                    browser = p.chromium.launch(headless=True, args=launch_args, timeout=10000)
                except Exception as ex:
                    launch_errors.append(f"default chromium: {ex}")

                # 2. Chrome system channel
                if browser is None:
                    try:
                        browser = p.chromium.launch(
                            channel="chrome",
                            headless=True,
                            args=launch_args,
                            timeout=10000,
                        )
                    except Exception as ex:
                        launch_errors.append(f"chrome channel: {ex}")

                # 3. Edge system channel
                if browser is None:
                    try:
                        browser = p.chromium.launch(
                            channel="msedge",
                            headless=True,
                            args=launch_args,
                            timeout=10000,
                        )
                    except Exception as ex:
                        launch_errors.append(f"msedge channel: {ex}")

                # 4. Explicit system executable paths
                if browser is None:
                    for exe_path in candidate_executables:
                        if os.path.isfile(exe_path):
                            try:
                                browser = p.chromium.launch(
                                    executable_path=exe_path,
                                    headless=True,
                                    args=launch_args,
                                    timeout=10000,
                                )
                                if browser:
                                    break
                            except Exception as ex:
                                launch_errors.append(f"executable {exe_path}: {ex}")

                if browser is None:
                    raise RuntimeError(
                        f"Could not launch any Chromium-compatible browser. "
                        f"Errors encountered: {'; '.join(launch_errors)}"
                    )

                page = None
                try:
                    page = browser.new_page()
                    # Set HTML content with network idle wait
                    page.set_content(html, wait_until="networkidle", timeout=30000)

                    # Ensure fonts are ready
                    try:
                        page.evaluate("document.fonts.ready")
                    except Exception as fe:
                        logger.debug(f"Fonts ready evaluation notice: {fe}")

                    page.wait_for_timeout(500)

                    format_size = page_size if page_size in ("A4", "Letter") else "A4"
                    pdf_bytes = page.pdf(
                        format=format_size,
                        print_background=True,
                        prefer_css_page_size=False,
                        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                        scale=0.92,
                    )
                    return pdf_bytes
                finally:
                    if page:
                        try:
                            page.close()
                        except Exception:
                            pass
                    try:
                        browser.close()
                    except Exception:
                        pass

        return await run_in_threadpool(_sync_generate)

    def _generate_with_weasyprint(
        self, html: str, page_size: str = "A4"
    ) -> bytes:
        """
        Generate PDF using WeasyPrint (fallback engine).

        Good quality, pure-Python solution. Doesn't require Chromium
        but may have minor CSS rendering differences.
        """
        try:
            from weasyprint import HTML

            pdf_bytes = HTML(string=html).write_pdf()
            if not pdf_bytes:
                raise ValueError("WeasyPrint produced empty PDF output")
            return pdf_bytes
        except ImportError:
            logger.error(
                "WeasyPrint is not installed. Install it with: "
                "pip install weasyprint"
            )
            raise RuntimeError(
                "No PDF engine available. Install either Playwright or WeasyPrint."
            )

    async def save_pdf(
        self,
        data: ResumeData,
        filename: str,
        template_id: Optional[str] = None,
    ) -> Path:
        """
        Generate a PDF and save it to the exports directory.

        Args:
            data: Complete resume data.
            filename: Output filename (without path).
            template_id: Override template.

        Returns:
            Path to the saved PDF file.
        """
        pdf_bytes = await self.generate_pdf(data, template_id)

        output_path = settings.export_path / filename
        output_path.write_bytes(pdf_bytes)

        logger.info(f"PDF saved to: {output_path}")
        return output_path


# Singleton instance
pdf_service = PDFService()
