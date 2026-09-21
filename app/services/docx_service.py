# =============================================================================
# Professional Resume Builder — DOCX (Word Document) Generation Service
# =============================================================================
"""
Generates clean, beautifully styled, ATS-compliant Microsoft Word (.docx)
resumes from structured ResumeData schemas using python-docx.
"""

import io
import logging
import re
from typing import Optional

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

from app.schemas.resume import ResumeData

logger = logging.getLogger(__name__)


def _set_cell_margins(cell, top=50, bottom=50, left=50, right=50):
    """Set padding for a table cell in twentieths of a point (dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def _add_horizontal_rule(paragraph, color_hex="94A3B8", size_eighths=8):
    """Adds a stylish bottom border line underneath a section heading."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:bottom w:val="single" w:sz="{size_eighths}" w:space="3" w:color="{color_hex}"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)


class DOCXService:
    """Service to compile ResumeData into structured, ATS-compliant Word documents."""

    def __init__(self):
        pass

    def generate_docx(self, data: ResumeData) -> bytes:
        """
        Compile ResumeData into a .docx byte stream.
        """
        if isinstance(data, dict):
            data = ResumeData(**data)

        doc = Document()

        # Set page size & margins (Standard 0.75-inch margins for high content density)
        sections = doc.sections
        for s in sections:
            s.top_margin = Inches(0.7)
            s.bottom_margin = Inches(0.7)
            s.left_margin = Inches(0.75)
            s.right_margin = Inches(0.75)
            if data.page_size == "Letter":
                s.page_width = Inches(8.5)
                s.page_height = Inches(11.0)
            else:
                s.page_width = Inches(8.27)
                s.page_height = Inches(11.69)

        # Configure Normal font style
        style_normal = doc.styles['Normal']
        style_normal.font.name = 'Calibri'
        style_normal.font.size = Pt(10)
        style_normal.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)  # #1f2937

        hidden = getattr(data, "hidden_sections", None) or []

        # =====================================================================
        # 1. HEADER (Name, Title, Contact Info)
        # =====================================================================
        name_text = data.full_name or "Your Name"
        p_name = doc.add_paragraph()
        p_name.paragraph_format.space_before = Pt(0)
        p_name.paragraph_format.space_after = Pt(2)
        p_name.paragraph_format.line_spacing = 1.05

        run_name = p_name.add_run(name_text)
        run_name.bold = True
        run_name.font.size = Pt(22)
        run_name.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)  # #0f172a

        if data.professional_title:
            p_title = doc.add_paragraph()
            p_title.paragraph_format.space_before = Pt(0)
            p_title.paragraph_format.space_after = Pt(4)
            p_title.paragraph_format.line_spacing = 1.1
            run_title = p_title.add_run(data.professional_title)
            run_title.bold = True
            run_title.font.size = Pt(11.5)
            run_title.font.color.rgb = RGBColor(0x47, 0x55, 0x69)  # #475569

        # Contact line
        contact_items = []
        if data.email:
            contact_items.append(f"Email: {data.email}")
        if data.phone:
            contact_items.append(f"Phone: {data.phone}")
        if data.address:
            contact_items.append(f"Location: {data.address}")
        if data.linkedin:
            contact_items.append(f"LinkedIn: {data.linkedin}")
        if data.github:
            contact_items.append(f"GitHub: {data.github}")
        if data.portfolio:
            contact_items.append(f"Portfolio: {data.portfolio}")
        if data.website:
            contact_items.append(f"Website: {data.website}")

        if contact_items:
            p_contact = doc.add_paragraph()
            p_contact.paragraph_format.space_before = Pt(0)
            p_contact.paragraph_format.space_after = Pt(10)
            p_contact.paragraph_format.line_spacing = 1.15
            run_contact = p_contact.add_run("  |  ".join(contact_items))
            run_contact.font.size = Pt(9)
            run_contact.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)

        # Helper to render section headings
        def add_section_heading(title: str):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(title.upper())
            run.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
            _add_horizontal_rule(p, color_hex="CBD5E1", size_eighths=8)
            return p

        # Order of sections
        section_order = getattr(data, "section_order", None)
        if not section_order:
            section_order = [
                "summary",
                "skills",
                "experience",
                "projects",
                "education",
                "certifications",
                "languages",
                "awards",
                "volunteer",
                "references",
            ]

        for sec in section_order:
            if sec in hidden:
                continue

            # =================================================================
            # SUMMARY
            # =================================================================
            if sec == "summary" and data.summary and data.summary.strip():
                add_section_heading("Professional Summary")
                lines = data.summary.strip().split("\n")
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    if line_clean.startswith(("* ", "- ", "• ")):
                        p = doc.add_paragraph(style='List Bullet')
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.line_spacing = 1.15
                        run = p.add_run(line_clean[2:].strip())
                        run.font.size = Pt(9.5)
                    else:
                        p = doc.add_paragraph()
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.space_after = Pt(4)
                        p.paragraph_format.line_spacing = 1.18
                        run = p.add_run(line_clean)
                        run.font.size = Pt(9.5)

            # =================================================================
            # SKILLS
            # =================================================================
            elif sec == "skills" and data.has_section("skills"):
                add_section_heading("Technical Skills")
                categories: dict[str, list[str]] = {}
                for s in data.skills:
                    cat = s.category or "Technical Skills"
                    cat_clean = cat.replace("_", " ").title()
                    if cat_clean not in categories:
                        categories[cat_clean] = []
                    if s.name and s.name not in categories[cat_clean]:
                        categories[cat_clean].append(s.name)

                for cat_title, skill_list in categories.items():
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(1)
                    p.paragraph_format.space_after = Pt(3)
                    p.paragraph_format.line_spacing = 1.15

                    run_cat = p.add_run(f"{cat_title}: ")
                    run_cat.bold = True
                    run_cat.font.size = Pt(9.5)
                    run_cat.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

                    run_skills = p.add_run(", ".join(skill_list))
                    run_skills.font.size = Pt(9.5)

            # =================================================================
            # EXPERIENCE
            # =================================================================
            elif sec == "experience" and data.has_section("experience"):
                add_section_heading("Professional Experience")
                for exp in data.experience:
                    # Role / Company line with dates
                    p_entry = doc.add_paragraph()
                    p_entry.paragraph_format.space_before = Pt(6)
                    p_entry.paragraph_format.space_after = Pt(2)
                    p_entry.paragraph_format.line_spacing = 1.15
                    p_entry.paragraph_format.keep_with_next = True

                    run_role = p_entry.add_run(exp.position or "Position")
                    run_role.bold = True
                    run_role.font.size = Pt(10)
                    run_role.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

                    company_text = f" — {exp.company}" if exp.company else ""
                    if exp.location:
                        company_text += f" ({exp.location})"
                    run_co = p_entry.add_run(company_text)
                    run_co.font.size = Pt(9.5)
                    run_co.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

                    # Date string
                    dates = []
                    if exp.start_date:
                        dates.append(exp.start_date)
                    if exp.is_current:
                        dates.append("Present")
                    elif exp.end_date:
                        dates.append(exp.end_date)
                    date_str = " – ".join(dates) if dates else ""

                    if date_str:
                        run_date = p_entry.add_run(f"  |  {date_str}")
                        run_date.font.size = Pt(9)
                        run_date.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

                    if exp.description:
                        lines = exp.description.strip().split("\n")
                        for line in lines:
                            line_clean = line.strip()
                            if not line_clean:
                                continue
                            if line_clean.startswith(("* ", "- ", "• ")):
                                p = doc.add_paragraph(style='List Bullet')
                                p.paragraph_format.space_before = Pt(0)
                                p.paragraph_format.space_after = Pt(1.5)
                                p.paragraph_format.line_spacing = 1.15
                                run = p.add_run(line_clean[2:].strip())
                                run.font.size = Pt(9.5)
                            else:
                                p = doc.add_paragraph()
                                p.paragraph_format.space_before = Pt(0)
                                p.paragraph_format.space_after = Pt(2)
                                p.paragraph_format.line_spacing = 1.15
                                run = p.add_run(line_clean)
                                run.font.size = Pt(9.5)

                    if exp.achievements:
                        for ach in exp.achievements:
                            if ach and ach.strip():
                                p = doc.add_paragraph(style='List Bullet')
                                p.paragraph_format.space_before = Pt(0)
                                p.paragraph_format.space_after = Pt(1.5)
                                p.paragraph_format.line_spacing = 1.15
                                run = p.add_run(ach.strip())
                                run.font.size = Pt(9.5)

            # =================================================================
            # PROJECTS
            # =================================================================
            elif sec == "projects" and data.has_section("projects"):
                add_section_heading("Projects")
                for proj in data.projects:
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(5)
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.line_spacing = 1.15
                    p.paragraph_format.keep_with_next = True

                    run_title = p.add_run(proj.title or "Project")
                    run_title.bold = True
                    run_title.font.size = Pt(10)

                    links = []
                    if proj.github_url:
                        links.append(f"GitHub: {proj.github_url}")
                    if proj.live_url:
                        links.append(f"Live: {proj.live_url}")
                    if links:
                        run_links = p.add_run(f" ({', '.join(links)})")
                        run_links.font.size = Pt(8.5)
                        run_links.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

                    if proj.date:
                        run_date = p.add_run(f"  |  {proj.date}")
                        run_date.font.size = Pt(8.5)
                        run_date.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

                    if proj.technologies:
                        p_tech = doc.add_paragraph()
                        p_tech.paragraph_format.space_before = Pt(0)
                        p_tech.paragraph_format.space_after = Pt(2)
                        run_tlabel = p_tech.add_run("Technologies: ")
                        run_tlabel.bold = True
                        run_tlabel.font.size = Pt(9)
                        run_tval = p_tech.add_run(", ".join(proj.technologies))
                        run_tval.font.size = Pt(9)
                        run_tval.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

                    if proj.description:
                        lines = proj.description.strip().split("\n")
                        for line in lines:
                            line_clean = line.strip()
                            if not line_clean:
                                continue
                            if line_clean.startswith(("* ", "- ", "• ")):
                                p_bul = doc.add_paragraph(style='List Bullet')
                                p_bul.paragraph_format.space_before = Pt(0)
                                p_bul.paragraph_format.space_after = Pt(1.5)
                                run = p_bul.add_run(line_clean[2:].strip())
                                run.font.size = Pt(9.5)
                            else:
                                p_desc = doc.add_paragraph()
                                p_desc.paragraph_format.space_before = Pt(0)
                                p_desc.paragraph_format.space_after = Pt(2)
                                run = p_desc.add_run(line_clean)
                                run.font.size = Pt(9.5)

                    if proj.highlights:
                        for h in proj.highlights:
                            if h and h.strip():
                                p_h = doc.add_paragraph(style='List Bullet')
                                p_h.paragraph_format.space_before = Pt(0)
                                p_h.paragraph_format.space_after = Pt(1.5)
                                run = p_h.add_run(h.strip())
                                run.font.size = Pt(9.5)

            # =================================================================
            # EDUCATION
            # =================================================================
            elif sec == "education" and data.has_section("education"):
                add_section_heading("Education")
                for edu in data.education:
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(5)
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.line_spacing = 1.15
                    p.paragraph_format.keep_with_next = True

                    degree_str = edu.degree or "Degree"
                    if edu.field_of_study:
                        degree_str += f" in {edu.field_of_study}"
                    run_deg = p.add_run(degree_str)
                    run_deg.bold = True
                    run_deg.font.size = Pt(10)

                    inst_str = f" — {edu.institution}" if edu.institution else ""
                    if edu.location:
                        inst_str += f" ({edu.location})"
                    run_inst = p.add_run(inst_str)
                    run_inst.font.size = Pt(9.5)

                    dates = []
                    if edu.start_date:
                        dates.append(edu.start_date)
                    if edu.is_current:
                        dates.append("Present")
                    elif edu.end_date:
                        dates.append(edu.end_date)
                    date_str = " – ".join(dates) if dates else ""
                    if edu.grade:
                        date_str += f" (GPA: {edu.grade})"

                    if date_str:
                        run_date = p.add_run(f"  |  {date_str}")
                        run_date.font.size = Pt(9)
                        run_date.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

                    if edu.description:
                        p_desc = doc.add_paragraph()
                        p_desc.paragraph_format.space_before = Pt(0)
                        p_desc.paragraph_format.space_after = Pt(2)
                        run_desc = p_desc.add_run(edu.description.strip())
                        run_desc.font.size = Pt(9.5)

            # =================================================================
            # CERTIFICATIONS
            # =================================================================
            elif sec == "certifications" and data.has_section("certifications"):
                add_section_heading("Certifications")
                for cert in data.certifications:
                    p = doc.add_paragraph(style='List Bullet')
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.line_spacing = 1.15
                    run_name = p.add_run(cert.name)
                    run_name.bold = True
                    run_name.font.size = Pt(9.5)
                    issuer_info = []
                    if cert.issuer:
                        issuer_info.append(cert.issuer)
                    if cert.date:
                        issuer_info.append(cert.date)
                    if issuer_info:
                        run_sub = p.add_run(f" — {' · '.join(issuer_info)}")
                        run_sub.font.size = Pt(9.5)
                        run_sub.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

            # =================================================================
            # LANGUAGES
            # =================================================================
            elif sec == "languages" and data.has_section("languages"):
                add_section_heading("Languages")
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(4)
                lang_items = []
                for lang in data.languages:
                    item = lang.name
                    if lang.fluency:
                        item += f" ({lang.fluency})"
                    lang_items.append(item)
                run = p.add_run(", ".join(lang_items))
                run.font.size = Pt(9.5)

            # =================================================================
            # AWARDS
            # =================================================================
            elif sec == "awards" and data.has_section("awards"):
                add_section_heading("Awards & Honors")
                for award in data.awards:
                    p = doc.add_paragraph(style='List Bullet')
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(2)
                    run = p.add_run(award.title)
                    run.bold = True
                    run.font.size = Pt(9.5)
                    meta = []
                    if award.issuer:
                        meta.append(award.issuer)
                    if award.date:
                        meta.append(award.date)
                    if meta:
                        run_meta = p.add_run(f" — {' · '.join(meta)}")
                        run_meta.font.size = Pt(9.5)

            # =================================================================
            # VOLUNTEER
            # =================================================================
            elif sec == "volunteer" and data.has_section("volunteer"):
                add_section_heading("Volunteer Experience")
                for vol in data.volunteer:
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(4)
                    p.paragraph_format.space_after = Pt(2)
                    run_role = p.add_run(vol.role or "Volunteer")
                    run_role.bold = True
                    run_role.font.size = Pt(10)
                    org_str = f" — {vol.organization}" if vol.organization else ""
                    if vol.location:
                        org_str += f" ({vol.location})"
                    run_org = p.add_run(org_str)
                    run_org.font.size = Pt(9.5)
                    if vol.description:
                        p_desc = doc.add_paragraph(style='List Bullet')
                        p_desc.paragraph_format.space_before = Pt(0)
                        p_desc.paragraph_format.space_after = Pt(2)
                        run_d = p_desc.add_run(vol.description.strip())
                        run_d.font.size = Pt(9.5)

        # Output bytes
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output.getvalue()


_docx_service: Optional[DOCXService] = None


def get_docx_service() -> DOCXService:
    global _docx_service
    if _docx_service is None:
        _docx_service = DOCXService()
    return _docx_service
