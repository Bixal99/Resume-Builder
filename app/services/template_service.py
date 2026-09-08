# =============================================================================
# Professional Resume Builder — Template Service
# =============================================================================
"""
Template rendering service using Jinja2.

Responsibilities:
- Discover available resume templates
- Render resume HTML from template + data
- Provide template metadata for the gallery UI
"""

from pathlib import Path
import re
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.schemas.resume import ResumeData, TemplateInfo


# --- Template Registry ---
# Each template is a directory under resume_templates/ containing:
#   - template.html  (Jinja2 template)
#   - styles.css     (template-specific styles)
TEMPLATE_REGISTRY: dict[str, TemplateInfo] = {
    "modern": TemplateInfo(
        id="modern",
        name="Modern Professional",
        description="Clean, ATS-friendly layout with strong typography hierarchy. "
                    "Perfect for tech companies and modern organizations.",
        category="professional",
        is_premium=False,
    ),
    "executive": TemplateInfo(
        id="executive",
        name="Executive Elegance",
        description="Luxury minimalism with serif headings and generous spacing, designed for senior professionals.",
        category="professional",
        is_premium=False,
    ),
    "contemporary": TemplateInfo(
        id="contemporary",
        name="Contemporary Clean",
        description="Modern layout with soft section dividers and sophisticated color highlights for high readability.",
        category="professional",
        is_premium=False,
    ),
    "ats": TemplateInfo(
        id="ats",
        name="Minimal ATS",
        description="Extremely optimized for Automated Tracking Systems. Simple, clean black-and-white layout.",
        category="minimal",
        is_premium=False,
    ),
    "tech": TemplateInfo(
        id="tech",
        name="Premium Tech",
        description="Designed specifically for developers and engineers, showcasing projects and technical skills cleanly.",
        category="creative",
        is_premium=False,
    ),
}


def parse_bullets(text: str) -> str:
    """Parse text with newlines and bullet points (* or -) into HTML lists and paragraphs."""
    if not text:
        return ""
    import html
    escaped_text = html.escape(text.strip())
    lines = escaped_text.split('\n')
    
    from markupsafe import Markup
    out = []
    in_list = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            if not in_list and i < len(lines) - 1:
                out.append("<br>")
            continue
            
        if line.startswith('* ') or line.startswith('- ') or line.startswith('• '):
            if not in_list:
                out.append('<ul class="resume-list" style="margin-top: 2px; margin-bottom: 2px; padding-left: 1.5em; list-style-type: disc;">')
                in_list = True
            out.append(f'<li style="margin-bottom: 1px;">{line[2:].strip()}</li>')
        else:
            if in_list:
                out.append('</ul>')
                in_list = False
            out.append(line)
            # Add <br> only if there's another normal line following immediately
            if i < len(lines) - 1 and lines[i+1].strip() != '':
                next_line = lines[i+1].strip()
                if not (next_line.startswith('* ') or next_line.startswith('- ') or next_line.startswith('• ')):
                    out.append("<br>")
            
    if in_list:
        out.append('</ul>')
        
    return Markup("".join(out))


def format_url(url: str) -> str:
    """Ensure URL has proper scheme for external navigation."""
    if not url:
        return ""
    url = str(url).strip()
    if url.startswith("http://") or url.startswith("https://") or url.startswith("mailto:") or url.startswith("tel:"):
        return url
    return f"https://{url}"


def reorder_html_sections(html: str, section_order: list[str]) -> str:
    if not section_order:
        return html

    # We want to find sections and reorder them.
    # A section is bounded by <section class="resume-section" data-section-type="..."> and </section>.
    pattern = re.compile(
        r'(<section\b[^>]*\bdata-section-type=["\']([^"\']+)["\'][^>]*>.*?</section>)',
        re.DOTALL
    )

    sections = {}
    matches = list(pattern.finditer(html))
    if not matches:
        return html

    # Extract the sections
    for match in matches:
        full_text = match.group(1)
        sec_type = match.group(2)
        sections[sec_type] = full_text

    # Let's find the span of the first match and the last match.
    first_start = matches[0].start()
    last_end = matches[-1].end()

    # Construct the reordered sections HTML
    reordered_parts = []
    # Loop over the custom order
    for sec_id in section_order:
        if sec_id in sections:
            reordered_parts.append(sections[sec_id])

    # Add any sections that were rendered but not present in section_order (safety fallback)
    for sec_type, sec_html in sections.items():
        if sec_type not in section_order:
            reordered_parts.append(sec_html)

    reordered_html = "\n\n".join(reordered_parts)

    # Reassemble the HTML
    new_html = html[:first_start] + reordered_html + html[last_end:]
    return new_html


class TemplateService:
    """
    Service for rendering resume templates.

    Uses Jinja2 with autoescaping enabled for XSS prevention.
    Templates are loaded from the filesystem and can be hot-reloaded
    in debug mode.
    """

    def __init__(self):
        """Initialize Jinja2 environment."""
        self.templates_dir = settings.resume_templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html"]),
            # Enable template caching in production, disable in debug
            auto_reload=settings.debug,
        )
        self.env.filters["parse_bullets"] = parse_bullets
        self.env.filters["format_url"] = format_url

    def render_resume(
        self,
        data: ResumeData,
        template_id: Optional[str] = None,
    ) -> str:
        """
        Render a resume to HTML using the specified template.

        Args:
            data: Complete resume data.
            template_id: Template directory name (e.g., "modern").
                         Falls back to data.template_id, then "modern".

        Returns:
            Rendered HTML string ready for display or PDF conversion.
        """
        tid = template_id or data.template_id or "modern"

        # Validate template exists
        if tid not in TEMPLATE_REGISTRY:
            tid = "modern"

        # Load template
        template_path = f"{tid}/template.html"
        template = self.env.get_template(template_path)

        # Load template-specific CSS
        css_path = self.templates_dir / tid / "styles.css"
        template_css = ""
        if css_path.exists():
            template_css = css_path.read_text(encoding="utf-8")

        hidden = getattr(data, "hidden_sections", None) or []

        # Render with full resume data context
        html = template.render(
            resume=data,
            template_css=template_css,
            page_size=data.page_size,
            # Convenience properties for template logic
            full_name=data.full_name,
            has_contact=data.has_contact_info,
            has_personal=data.has_personal_info,
            # Section visibility flags
            has_summary=bool(data.summary and data.summary.strip()) and "summary" not in hidden,
            has_education=data.has_section("education") and "education" not in hidden,
            has_experience=data.has_section("experience") and "experience" not in hidden,
            has_projects=data.has_section("projects") and "projects" not in hidden,
            has_skills=data.has_section("skills") and "skills" not in hidden,
            has_languages=data.has_section("languages") and "languages" not in hidden,
            has_certifications=data.has_section("certifications") and "certifications" not in hidden,
            has_awards=data.has_section("awards") and "awards" not in hidden,
            has_volunteer=data.has_section("volunteer") and "volunteer" not in hidden,
            has_references=data.has_section("references") and "references" not in hidden,
        )

        # Apply section reordering if section_order is specified
        order = getattr(data, "section_order", None)
        if order:
            html = reorder_html_sections(html, order)

        return html

    def get_available_templates(self) -> list[TemplateInfo]:
        """
        Get a list of all available resume templates.

        Only returns templates that exist on the filesystem.
        """
        available = []
        for tid, info in TEMPLATE_REGISTRY.items():
            template_path = self.templates_dir / tid / "template.html"
            if template_path.exists():
                available.append(info)
        return available

    def get_template_info(self, template_id: str) -> Optional[TemplateInfo]:
        """Get metadata for a specific template."""
        return TEMPLATE_REGISTRY.get(template_id)

    def template_exists(self, template_id: str) -> bool:
        """Check if a template exists on the filesystem."""
        template_path = self.templates_dir / template_id / "template.html"
        return template_path.exists()


# Singleton instance
template_service = TemplateService()
