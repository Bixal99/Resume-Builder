import json
import logging
import os
import re
import uuid
from typing import Optional
import fitz  # PyMuPDF
import httpx
from huggingface_hub import InferenceClient

from app.core.config import settings
from app.schemas.resume import ResumeData

logger = logging.getLogger(__name__)

# Primary models on HF router (ordered for speed and warm throughput)
SUPPORTED_MODELS = [
    "meta-llama/Llama-3.1-8B-Instruct",
    "Qwen/Qwen2.5-Coder-32B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct"
]


def heal_split_tokens(text: str) -> str:
    """
    Heals split words, emails, phone numbers, and URLs caused by narrow column wrapping in PDFs.
    E.g.
    - 'bilalnadeema302003@gmail.co\\nm' -> 'bilalnadeema302003@gmail.com'
    - 'LinkedI\\nn' -> 'LinkedIn'
    - 'GitHu\\nb' -> 'GitHub'
    - 'Portfoli\\no' -> 'Portfolio'
    - 'Websit\\ne' -> 'Website'
    - '+974\\n55470358' -> '+974 55470358'
    - 'Doha,\\nQatar' -> 'Doha, Qatar'
    """
    if not text:
        return ""
    # Broken email domains (.co\nm, @gmail.\ncom, etc.)
    text = re.sub(r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+)\s*\n\s*([A-Za-z]{1,4})\b', r'\1\2', text)
    text = re.sub(r'([A-Za-z0-9._%+-]+@)\s*\n\s*([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b', r'\1\2', text)
    
    # Broken common contact labels
    text = re.sub(r'\bLinkedI\s*\n\s*n\b', 'LinkedIn', text, flags=re.I)
    text = re.sub(r'\bGitHu\s*\n\s*b\b', 'GitHub', text, flags=re.I)
    text = re.sub(r'\bPortfoli\s*\n\s*o\b', 'Portfolio', text, flags=re.I)
    text = re.sub(r'\bWebsit\s*\n\s*e\b', 'Website', text, flags=re.I)
    
    # Broken URLs split across lines: e.g. linkedin.com/\nin/..., https://\ngithub.com/...
    text = re.sub(r'((?:https?://|www\.)[^\s\n]+)\s*\n\s*([a-zA-Z0-9_\-\./\?&=%]+)', r'\1\2', text)
    text = re.sub(r'(linkedin\.com/(?:in|company)/)\s*\n\s*([a-zA-Z0-9_\-]+)', r'\1\2', text, flags=re.I)
    
    # Broken phone numbers: e.g. +974\n55470358 -> +974 55470358
    text = re.sub(r'(\+\d{1,4})\s*\n\s*(\d{5,12})\b', r'\1 \2', text)
    
    # Broken location: e.g. Doha,\nQatar -> Doha, Qatar
    text = re.sub(r'([A-Za-z]+,)\s*\n\s*([A-Za-z]+)\b', r'\1 \2', text)
    return text


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from a digital PDF using PyMuPDF.
    Sorts blocks by physical layout (Y, then X) to preserve document structure.
    Also extracts all embedded hyperlink annotations and associates them with anchor words.
    """
    try:
        doc = fitz.open("pdf", file_bytes)
        text = ""
        embedded_links = []

        for page_idx, page in enumerate(doc):
            # Extract text blocks
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (round(b[1] / 10), b[0]))
            for b in blocks:
                if b[6] == 0:  # text block
                    text += b[4].strip() + "\n\n"

            # Extract hyperlink annotations
            for link in page.get_links():
                uri = (link.get("uri") or "").strip()
                if not uri:
                    continue
                # Normalize schemes: handle www., drive.google.com, linkedin.com without explicit https://
                if not (uri.startswith("http://") or uri.startswith("https://") or uri.startswith("mailto:") or uri.startswith("tel:")):
                    if uri.startswith("www.") or ("." in uri and not uri.startswith("javascript:") and not uri.startswith("#")):
                        uri = "https://" + uri
                    else:
                        continue
                rect = link.get("from")
                anchor_text = page.get_textbox(rect).strip() if rect else ""
                if not anchor_text and rect:
                    anchor_text = page.get_textbox(fitz.Rect(rect.x0 - 5, rect.y0 - 5, rect.x1 + 10, rect.y1 + 5)).strip()
                # Expand context horizontally across the page to capture project title, labels, and dates on the same line
                context = ""
                if rect:
                    line_x0 = max(0, rect.x0 - 350)
                    line_x1 = min(page.rect.width, rect.x1 + 350)
                    line_y0 = max(0, rect.y0 - 8)
                    line_y1 = rect.y1 + 8
                    ctx_rect = fitz.Rect(line_x0, line_y0, line_x1, line_y1)
                    context = page.get_textbox(ctx_rect).strip().replace("\n", " ")
                
                clean_anchor = re.sub(r'\s+', ' ', anchor_text).strip()
                clean_context = re.sub(r'\s+', ' ', context).strip()
                embedded_links.append({
                    "anchor": clean_anchor,
                    "context": clean_context,
                    "uri": uri
                })
        
        text = heal_split_tokens(text.strip())
        if not text:
            raise ValueError("No extractable text found in the PDF. Scanned images are not currently supported.")

        # If any embedded hyperlinks were detected, append them explicitly so the AI sees real URLs
        if embedded_links:
            text += "\n\n--- EMBEDDED HYPERLINKS IN RESUME ---\n"
            seen_items = set()
            for item in embedded_links:
                key = (item["uri"], item["anchor"], item["context"])
                if key in seen_items:
                    continue
                seen_items.add(key)
                anchor = re.sub(r'\s+', ' ', (item["anchor"] or "Link")).replace("'", " ").strip()
                clean_ctx = re.sub(r'\s+', ' ', (item["context"] or "")).replace("'", " ").strip()
                ctx = f" (Context: '{clean_ctx}')" if clean_ctx and clean_ctx != anchor else ""
                text += f"- Anchor: '{anchor}'{ctx} -> Target URL: {item['uri']}\n"
            
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        raise ValueError(f"Could not read PDF file: {str(e)}")


SUPPORTED_FONT_FAMILY_MAP = [
    ("poppins", "'Poppins', sans-serif"),
    ("roboto", "'Roboto', sans-serif"),
    ("arial", "Arial, sans-serif"),
    ("helvetica", "Arial, sans-serif"),
    ("calibri", "Arial, sans-serif"),
    ("segoe", "Arial, sans-serif"),
    ("liberationsans", "Arial, sans-serif"),
    ("opensans", "'Open Sans', sans-serif"),
    ("open sans", "'Open Sans', sans-serif"),
    ("dejavusans", "'Open Sans', sans-serif"),
    ("lato", "'Lato', sans-serif"),
    ("montserrat", "'Montserrat', sans-serif"),
    ("oswald", "'Oswald', sans-serif"),
    ("merriweather", "'Merriweather', serif"),
    ("playfair", "'Playfair Display', serif"),
    ("lora", "'Lora', serif"),
    ("georgia", "Georgia, serif"),
    ("timesnewroman", "'Times New Roman', Times, serif"),
    ("times", "'Times New Roman', Times, serif"),
]


def detect_pdf_font(file_bytes: bytes) -> Optional[str]:
    """
    Inspects text span font families across all pages in the PDF.
    Counts character volume per font family to identify the dominant document typeface.
    Maps to the closest supported font family for document theme settings.
    """
    if not file_bytes:
        return None
    try:
        doc = fitz.open("pdf", file_bytes)
        font_counts: dict[str, int] = {}
        for page in doc:
            d = page.get_text("dict")
            for block in d.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font_name = str(span.get("font", "")).strip().lower()
                        text = span.get("text", "")
                        if font_name and text.strip():
                            font_counts[font_name] = font_counts.get(font_name, 0) + len(text)
        
        if not font_counts:
            return None
        
        # Sort fonts by total character count descending
        sorted_fonts = sorted(font_counts.items(), key=lambda x: x[1], reverse=True)
        for raw_font, _ in sorted_fonts:
            cleaned = raw_font.replace("-", "").replace(" ", "").replace("_", "").lower()
            for key, val in SUPPORTED_FONT_FAMILY_MAP:
                k_clean = key.replace(" ", "").lower()
                if k_clean in cleaned or key in raw_font.lower():
                    logger.info(f"Detected dominant PDF font '{raw_font}' mapped to '{val}'")
                    return val
                    
        return None
    except Exception as e:
        logger.warning(f"Font detection notice: {e}")
        return None



def extract_profile_photo_from_pdf(file_bytes: bytes) -> Optional[str]:
    """
    Attempts to dynamically extract a candidate profile photo / headshot from the PDF.
    Inspects page 0 for embedded images, filtering out decorative icons, bullets,
    and full-page backgrounds based on aspect ratio and dimensions.
    Returns a base64 data URI (e.g. 'data:image/jpeg;base64,...') or None if not found.
    """
    if not file_bytes:
        return None
    try:
        import base64
        doc = fitz.open("pdf", file_bytes)
        if len(doc) == 0:
            return None
        page = doc[0]
        image_list = page.get_images(full=True)
        if not image_list:
            return None

        best_candidate = None
        best_score = -1

        for img_info in image_list:
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue
            if not base_image:
                continue

            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            ext = base_image.get("ext", "jpeg").lower()
            image_bytes = base_image.get("image")

            if not image_bytes or width < 50 or height < 50:
                # Too small: icons, bullets, tiny design elements
                continue

            if width > 1600 or height > 1600:
                # Too large: full page scans or background art
                continue

            aspect_ratio = width / max(1, height)
            # Profile photos are typically portrait or square (0.55 <= aspect <= 1.6)
            if 0.55 <= aspect_ratio <= 1.6:
                size_score = min(width, height)
                square_score = 1.0 - abs(aspect_ratio - 1.0)
                score = size_score * (1.0 + square_score)
                if score > best_score:
                    best_score = score
                    mime_type = "image/jpeg" if ext in ("jpg", "jpeg") else ("image/png" if ext == "png" else f"image/{ext}")
                    b64 = base64.b64encode(image_bytes).decode("utf-8")
                    best_candidate = f"data:{mime_type};base64,{b64}"

        return best_candidate
    except Exception as e:
        logger.warning(f"Profile photo extraction notice: {e}")
        return None



def _get_system_and_user_prompts(text: str):
    words = text.split()
    if len(words) > 10000:
        text = " ".join(words[:10000])

    minimal_schema = {
        "photo": None, "first_name": "", "last_name": "", "professional_title": "", "email": "", "phone": "",
        "address": "", "linkedin": "", "github": "", "portfolio": "", "website": "", "nationality": "", "summary": "",
        "education": [{"degree": "", "field_of_study": "", "institution": "", "location": "", "start_date": "", "end_date": "", "is_current": False, "grade": ""}],
        "experience": [{"company": "", "position": "", "location": "", "start_date": "", "end_date": "", "is_current": False, "achievements": [""]}],
        "projects": [{"title": "", "date": "", "description": "", "technologies": [""], "github_url": "", "live_url": "", "highlights": [""]}],
        "skills": [{"name": "", "category": "Technical Skills", "proficiency": 5}],
        "languages": [{"name": "", "fluency": ""}],
        "certifications": [{"name": "", "issuer": "", "date": "", "expiry_date": "", "credential_url": ""}],
        "awards": [{"title": "", "issuer": "", "date": "", "description": ""}],
        "volunteer": [{"organization": "", "role": "", "location": "", "start_date": "", "end_date": "", "is_current": False, "description": ""}]
    }
    
    schema_json = json.dumps(minimal_schema, indent=2)
    system_prompt = """You are an elite, highly intelligent Resume Parsing AI. 
Your job is to extract information from the user's raw resume text and output ONLY a valid JSON object.
The JSON object MUST strictly adhere to the following JSON structure (omit empty fields):
__SCHEMA__

CRITICAL PARSING RULES:
1. ZERO ALTERATION: Extract exact wording. DO NOT summarize or shorten text.
2. WORK EXPERIENCE (DYNAMIC):
   Extract all professional roles, full-time/part-time employment, internships, co-ops, apprenticeships, and freelance contracts into "experience".
   Look for sections titled "Work Experience", "Professional Experience", "Experience", "Employment", "Work History", "Internships", "Relevant Experience", etc.
   - 'company': Company, organization, or employer name.
   - 'position': Job title or role (e.g. "Software Engineer", "Frontend Developer Intern").
   - 'location': City, State/Country or "Remote" (or empty string).
   - 'start_date' and 'end_date': Dates as listed (e.g. "Jan 2022", "2024", or "Present").
   - 'is_current': True if currently employed or "Present".
   - 'achievements': Array of STAR bullet points or responsibilities.
   CRITICAL: If the resume contains ANY work experience or internships, ALWAYS extract every entry into 'experience'. If the resume does NOT contain any work experience (e.g. student/fresh graduate with only projects and education), leave "experience" as an empty array [].
3. VOLUNTEER/EXTRACURRICULAR: Any role like "President", "Club Lead", or student organizations must go into "volunteer".
4. EMPTY SECTIONS: If a section doesn't exist, leave its array empty []. NEVER output "None", "N/A", or dummy data.
5. SKILLS & CATEGORIES (CRITICAL):
   Do NOT merge all skills into one category!
   Assign each skill to one of these standard categories:
   - "Technical Skills" (Programming languages, databases, computer vision, algorithms, etc.)
   - "Frameworks & Libraries" (React, Next.js, Django, FastAPI, PyTorch, NumPy, Pandas, etc.)
   - "Tools & Platforms" (Git, GitHub, Docker, VS Code, Linux, Postman, Figma, Cloud platforms, Wireshark, Google Colab, etc.)
   - "Soft Skills" (Communication, Leadership, Problem Solving, Teamwork, etc.)
   Or use the explicit category header from the resume text.
   For EVERY skill:
   - 'name': specific skill name (e.g. "Python", "Next.js", "Docker", "Git", "GitLab CI/CD").
   - 'category': its category ("Technical Skills", "Frameworks & Libraries", "Tools & Platforms", or "Soft Skills").
   CRITICAL: Extract 100% of all skills listed across all categories without truncating or stopping early. Capture all tools and platforms through the very end of the list (e.g. Wireshark, Google Colab, Replit, GitLab CI/CD).
6. EDUCATION DEGREE & FIELD OF STUDY (CRITICAL):
   Strictly separate the degree qualification/level from the academic field of study!
   - 'degree': ONLY the degree qualification/title (e.g. "Bachelor of Science", "Bachelor of Arts", "Bachelor of Engineering", "Bachelor of Technology", "Master of Science", "Master of Business Administration", "Doctor of Philosophy", "Associate of Science", "High School Diploma").
   - 'field_of_study': ONLY the major, discipline, or field of study (e.g. "Computer Science", "Software Engineering", "Mechanical Engineering", "Electrical Engineering", "Data Science", "Economics", "Business Administration").
   NEVER put the field of study inside 'degree'!
   Example: If the resume says "Bachelor of Science in Computer Science", you MUST output:
   "degree": "Bachelor of Science", "field_of_study": "Computer Science".
   Example: If the resume says "BS Computer Science" or "B.S. in CS", you MUST output:
   "degree": "Bachelor of Science", "field_of_study": "Computer Science".
   Example: If the resume says "Master of Science in Data Science", you MUST output:
   "degree": "Master of Science", "field_of_study": "Data Science".
7. LINKS & URLS (CRITICAL):
   - Extract real destination URLs for 'linkedin', 'github', 'portfolio', 'website', 'github_url', and 'live_url'.
   - Check both the resume text AND the '--- EMBEDDED HYPERLINKS IN RESUME ---' section at the bottom of the document.
   - LINKEDIN (CRITICAL): If a LinkedIn link exists anywhere in the text or '--- EMBEDDED HYPERLINKS IN RESUME ---' (or contains 'linkedin.com'), you MUST extract the full URL into the 'linkedin' field! NEVER omit or leave 'linkedin' empty when a link or profile exists!
   - PROJECT LINKS (CRITICAL): In the Projects section, project titles often have anchor links right next to them, such as 'GitHub' and 'Live' (e.g. 'AI Book Assistant GitHub Live June 2026'). You MUST match each project to its corresponding embedded URLs:
     * Put the GitHub repository or code link into that project's 'github_url' field!
     * Put the live website, deployment, or demo link into that project's 'live_url' field!
     * Look at the Context in '--- EMBEDDED HYPERLINKS IN RESUME ---' to match the link to the exact project title!
     * NEVER leave 'github_url' empty when a GitHub link exists for the project!
   - NEVER, UNDER ANY CIRCUMSTANCES, output generic label words like "LinkedIn", "GitHub", "Portfolio", "Website", "Live", "Demo", or "Link" as the URL value! A URL must be an actual web destination (e.g. "https://linkedin.com/in/username", "https://github.com/username/repo", "https://myportfolio.dev").
   - If no valid URL or handle exists for a field, set it to empty string "". NEVER output dummy text!
8. EDUCATION GRADE:
   Extract GPA, grades, or academic standing (e.g. "2.85/4.0", "3.8 GPA") into the 'grade' field of education.
9. CERTIFICATIONS & CERTIFICATES (CRITICAL):
   Extract ALL certifications, certificates, licenses, credentials, and courses from sections titled "Certifications", "Certificates", "Licenses & Certifications", "Courses", etc. into the "certifications" array.
   - 'name': Exact certification name or title (e.g. "Critical Thinking", "Effective Leadership", "AWS Certified Solutions Architect").
   - 'issuer': Issuing organization or platform (e.g. "Deloitte WorldClass", "Coursera", "Google", "Amazon Web Services", or empty string).
   - 'date': Date or month/year (e.g. "September 8, 2026", "Sept 2023", "2024", or empty string).
   - 'expiry_date': Expiration date (or empty string).
   - 'credential_url': If this certification has a link, credential URL, certificate URL, or verify link (e.g. from '--- EMBEDDED HYPERLINKS IN RESUME ---' with anchor 'Credential', 'Verify', 'Certificate', 'Link', or matching the certification name / issuer, or Google Drive / Credly / Coursera link), you MUST extract that URL into 'credential_url'!
   CRITICAL CREDENTIAL LABELS RULE:
   - NEVER output words like "Credential", "Certificate", "Verify", "Link", or "View" as a certification 'name'! These are link labels or anchors, NOT the name of a certificate.
   CRITICAL DATES RULE:
   - NEVER output a date, month, or day-month (e.g. "9 sept", "sept", "September", "2024") as a certification 'name'!
   - When a certification entry is followed by or aligned with a date (e.g. "bbb  9 sept" or "bbb" on one line and "9 sept" on the next), "bbb" is the 'name' and "9 sept" is the 'date'.
   - Example:
     bbb    9 sept
     ssc    9 sept
     Output MUST be:
     [
       {"name": "bbb", "issuer": "", "date": "9 sept", "expiry_date": "", "credential_url": ""},
       {"name": "ssc", "issuer": "", "date": "9 sept", "expiry_date": "", "credential_url": ""}
     ]
   - ALWAYS extract every single certification. NEVER drop them!
10. AWARDS & ACHIEVEMENTS:
   Extract ALL awards, achievements, honors, competition wins, hackathons, and recognitions from sections titled "Achievements", "Key Achievements", "Awards", "Honors & Awards", "Accomplishments", "Awards & Achievements", etc. into the "awards" array.
   - 'title': Achievement or award title.
   - 'issuer': Issuing body, competition, university, or company, or empty string.
   - 'date': Date or year, or empty string.
   - 'description': Full achievement details or bullet description.
   CRITICAL: Standalone "Achievements" sections MUST be extracted into 'awards'. NEVER omit achievements!
11. LANGUAGES (CRITICAL):
   Extract ALL spoken languages into the "languages" array:
   - 'name': Language name (e.g. "English", "Urdu", "Arabic").
   - 'fluency': Proficiency level (e.g. "Fluent", "Native", "Beginner", "Intermediate", "Conversational", or empty string).
   CRITICAL HORIZONTAL / MULTI-LANGUAGE RULE:
   - When languages are listed horizontally, side-by-side, or on a single line (e.g. "English (Fluent)  Urdu (Fluent)  Arabic (Beginner)"), you MUST extract EACH language as a separate object in the array!
   - Example:
     Input: "English (Fluent)   Urdu (Fluent)   Arabic (Beginner)"
     Output:
     [
       {"name": "English", "fluency": "Fluent"},
       {"name": "Urdu", "fluency": "Fluent"},
       {"name": "Arabic", "fluency": "Beginner"}
     ]
   - NEVER omit or drop any language from the resume!
12. SKILLS & CATEGORIES (CRITICAL):
    - Extract ALL skills, technologies, frameworks, tools, libraries, languages, and platforms mentioned in the resume into the "skills" array:
      * 'name': The specific skill or technology name (e.g. "Python", "React.js", "Docker", "PostgreSQL", "C++", "C", "AI", "ML", "RAG", "OCR", "OOP", "SDLC", "Fast API", "Streamlit", "better auth").
      * 'category': The category heading under which it appears (e.g. "Technical Skills", "Frameworks & Libraries", "Tools & Platforms", "Programming Languages").
    - NEVER, UNDER ANY CIRCUMSTANCES, extract section or sub-section header fragments as a skill name!
      * For example: "Frameworks &", "Tools &", "Libraries", "Platforms", "Technical Skills", "Programming Languages" are CATEGORY HEADERS or header fragments, NEVER individual skills!
      * NEVER include words ending with "&" as a skill!
    - DO NOT DROP OR SKIP ANY SKILLS! If the resume lists 50, 60, or 90 skills across multiple categories or sub-headers, you MUST extract EVERY SINGLE ONE OF THEM into the "skills" array!
13. Output raw JSON only. Do not wrap in markdown or explanation.
""".replace("__SCHEMA__", schema_json)
    user_prompt = f"Here is the resume text:\n\n{text}"
    return system_prompt, user_prompt


def extract_json_from_text(t: str) -> str:
    t = t.strip()
    start = t.find('{')
    end = t.rfind('}')
    if start != -1 and end != -1 and end > start:
        return t[start:end+1]
    return t


def clean_dict(d):
    if isinstance(d, dict):
        cleaned = {}
        for k, v in d.items():
            v_clean = clean_dict(v)
            if v_clean not in (None, "", [], {}):
                cleaned[k] = v_clean
        return cleaned
    elif isinstance(d, list):
        cleaned = []
        for item in d:
            item_clean = clean_dict(item)
            if item_clean not in (None, "", [], {}):
                cleaned.append(item_clean)
        return cleaned
    else:
        if isinstance(d, str):
            s = d.strip().lower()
            if s in ("none", "null", "n/a", "na", "undefined"):
                return None
        return d


def normalize_skill_category(cat: str) -> str:
    if not cat:
        return "Technical Skills"
    c = str(cat).strip().rstrip(":").lower()
    c = c.replace("&amp;", "&").replace("  ", " ")
    if any(k in c for k in ("framework", "framwork", "librar")):
        return "Frameworks & Libraries"
    if any(k in c for k in ("tool", "platform", "devops")):
        return "Tools & Platforms"
    if any(k in c for k in ("soft", "interpersonal", "management")):
        return "Soft Skills"
    if any(k in c for k in ("tech", "language", "coding", "program", "competenc")):
        return "Technical Skills"
    return str(cat).strip().rstrip(":")


DISALLOWED_SKILL_NAMES = {
    # Main section headers
    "skills", "technical skills", "technical proficiencies", "technical", "core competencies",
    "soft skills", "hard skills", "proficiencies", "competencies", "qualifications",
    # Sub-category headers and fragments
    "frameworks & libraries", "frameworks and libraries", "frameworks &", "frameworks and", "frameworks",
    "framworks & libraries", "framworks &", "framworks", "libraries & frameworks", "libraries",
    "tools & platforms", "tools and platforms", "tools &", "tools and", "tools", "platforms",
    "tools & technologies", "tools and technologies", "technologies & tools", "technologies",
    "programming languages", "programming language", "programming", "languages", "language",
    "databases & cloud", "databases", "cloud & devops", "cloud platforms", "devops",
    "web technologies", "developer tools", "operating systems", "methodologies",
    "frontend", "backend", "full stack", "data science", "machine learning & ai",
    # Resume structural words
    "summary", "profile", "professional summary", "about me", "experience", "work experience",
    "education", "projects", "certifications", "certificates", "awards", "contact", "links",
    "portfolio", "website", "github", "linkedin", "email", "phone", "address"
}


def is_valid_skill_name(name: str) -> bool:
    if not name:
        return False
    s = name.strip()
    if len(s) == 0 or len(s) > 80:
        return False
    if "->" in s or "target url:" in s.lower() or "anchor:" in s.lower() or "embedded hyperlinks" in s.lower():
        return False
    if len(s) == 1 and s.upper() not in ("C", "R"):
        return False
    if re.match(r'^\d+$', s) or re.match(r'^(19|20)\d{2}$', s):
        return False
    if s.endswith("&") or s.startswith("&"):
        return False
    if s.endswith(":") or s.startswith(":"):
        return False
    if s.endswith("/") or s.startswith("/"):
        return False
    if s.endswith("-") or s.startswith("-"):
        return False
    s_low = s.rstrip(":").strip().lower()
    if s_low in DISALLOWED_SKILL_NAMES:
        return False
    if s_low.endswith(" &") or s_low.endswith(" and"):
        return False
    if s_low.startswith("& ") or s_low.startswith("and "):
        return False
    if re.match(r'^(frameworks?|tools?|libraries|platforms?|technologies|languages?)\s*(&|and)?$', s_low):
        return False
    return True


def build_skill_category_map(raw_text: str):
    """
    Scans the raw resume text for explicit skills section headers and subcategories.
    E.g.
    Technical Skills: Python, SQL, ...
    Frameworks & Libraries: Next.js, React.js, ...
    Tools & Platforms: Git, Docker, ...
    
    Returns:
      (skill_to_cat_dict, list_of_detected_categories, raw_skills_dict)
    """
    if not raw_text:
        return {}, [], {}
    skill_to_cat = {}
    cat_headers = []
    raw_skills = {}
    
    # Locate skills section
    sec_content = extract_section_raw(raw_text, r'TECHNICAL\s+SKILLS|TECHNICAL\s+PROFICIENCIES|CORE\s+COMPETENCIES|SKILLS') or raw_text
    
    current_cat = None
    lines = [line.strip() for line in sec_content.split('\n') if line.strip()]
    i = 0
    while i < len(lines):
        line_s = lines[i]
        i += 1
        
        # Stop parsing only if a distinct, major resume section header is hit
        clean_header_candidate = line_s.rstrip(":").strip()
        is_subcat_header = clean_header_candidate.lower() in (
            "languages", "programming languages", "coding languages", "technical skills",
            "frameworks", "frameworks & libraries", "tools", "tools & platforms", "technologies",
            "libraries", "platforms", "databases", "cloud & devops", "devops"
        )
        if not is_subcat_header and any(re.match(rf'^{h}$', clean_header_candidate, re.IGNORECASE) for h in [
            r'CERTIFICATIONS', r'CERTIFICATES', r'LICENSES(?:\s*&\s*CERTIFICATIONS)?',
            r'SPOKEN\s+LANGUAGES', r'EDUCATION', r'EXPERIENCE', r'WORK\s+EXPERIENCE', r'PROJECTS', r'AWARDS', r'VOLUNTEER'
        ]):
            current_cat = None
            break

        # Check if line ends with '&' or is a known category fragment (e.g. "Frameworks &", "Tools &")
        # and look ahead to next line to combine it (e.g. "Libraries:" or "Platforms:")
        if (line_s.endswith("&") or line_s.lower().endswith(" and")) and i < len(lines):
            next_line = lines[i]
            combined = f"{line_s} {next_line}".strip()
            if combined.endswith(":") or any(cat in combined.lower() for cat in ("libraries", "platforms", "technologies", "tools", "frameworks")):
                line_s = combined
                i += 1  # consume next line as part of the header

        # Check for sub-header lines like "Category Name:" or "Category Name: skill1, skill2..."
        m = re.match(r'^([A-Za-z0-9\s&/\-_]+):\s*(.*)$', line_s)
        clean_line_no_colon = line_s.rstrip(":").strip()
        
        # Skip section titles like "SKILLS" at the start of section
        if clean_line_no_colon.upper() in ("SKILLS", "TECHNICAL SKILLS", "TECHNICAL PROFICIENCIES", "CORE COMPETENCIES") and not m:
            continue

        is_standalone_cat = (
            not m and 
            clean_line_no_colon.lower() in DISALLOWED_SKILL_NAMES and
            any(k in clean_line_no_colon.lower() for k in ("skill", "framework", "tool", "platform", "language", "database", "cloud", "competenc"))
        )

        if m:
            cat_name = m.group(1).strip()
            # Ignore non-skill headers
            if cat_name.lower() not in ("email", "phone", "address", "date", "gpa", "degree", "title", "contact", "links"):
                current_cat = normalize_skill_category(cat_name)
                if current_cat not in cat_headers:
                    cat_headers.append(current_cat)
                rest = m.group(2).strip()
                if rest:
                    for s in re.split(r'[,;|•·\t]|\s+/\s+|\s{2,}', rest):
                        s_clean = s.strip()
                        if is_valid_skill_name(s_clean):
                            skill_to_cat[s_clean.lower()] = current_cat
                            raw_skills[s_clean.lower()] = (s_clean, current_cat)
        elif is_standalone_cat:
            current_cat = normalize_skill_category(clean_line_no_colon)
            if current_cat not in cat_headers:
                cat_headers.append(current_cat)
        elif current_cat:
            for s in re.split(r'[,;|•·\t]|\s+/\s+|\s{2,}', line_s):
                s_clean = s.strip()
                if is_valid_skill_name(s_clean):
                    skill_to_cat[s_clean.lower()] = current_cat
                    raw_skills[s_clean.lower()] = (s_clean, current_cat)
                    
    return skill_to_cat, cat_headers, raw_skills


def normalize_degree_name(d: str) -> str:
    d_clean = (d or "").strip()
    d_low = d_clean.lower()
    if d_low in ("bs", "b.s.", "bsc", "b.sc.", "b.sc"):
        return "Bachelor of Science"
    if d_low in ("ba", "b.a."):
        return "Bachelor of Arts"
    if d_low in ("be", "b.e."):
        return "Bachelor of Engineering"
    if d_low in ("btech", "b.tech", "b.tech."):
        return "Bachelor of Technology"
    if d_low in ("ms", "m.s.", "msc", "m.sc.", "m.sc"):
        return "Master of Science"
    if d_low in ("ma", "m.a."):
        return "Master of Arts"
    if d_low in ("mba", "m.b.a."):
        return "Master of Business Administration"
    if d_low in ("phd", "ph.d.", "dphil"):
        return "Doctor of Philosophy"
    return d_clean


def split_degree_and_field(degree: str, field_of_study: str):
    degree = (degree or "").strip()
    field = (field_of_study or "").strip()
    if not degree:
        return degree, field
    
    # If field is already provided, clean degree if it still contains "in <field>"
    if field:
        degree = re.sub(rf'\s+(?:in|–|-|—)\s+{re.escape(field)}[\.\s]*$', '', degree, flags=re.IGNORECASE).strip()
        return normalize_degree_name(degree), field

    # Field is empty; extract from degree string
    # Pattern 1: "... in <field>" (e.g. "Bachelor of Science in Computer Science")
    m_in = re.search(r'^(.*?)\s+in\s+(.+)$', degree, re.IGNORECASE)
    if m_in:
        d = m_in.group(1).strip().rstrip('.,;')
        f = m_in.group(2).strip().rstrip('.,;')
        if d and f:
            return normalize_degree_name(d), f

    # Pattern 2: "... - <field>" or "... – <field>" or "... — <field>"
    m_dash = re.search(r'^(.*?)\s+[-–—]\s+(.+)$', degree)
    if m_dash:
        d = m_dash.group(1).strip().rstrip('.,;')
        f = m_dash.group(2).strip().rstrip('.,;')
        if d and f:
            return normalize_degree_name(d), f

    # Pattern 3: "... ( <field> )"
    m_paren = re.search(r'^(.*?)\s*\(([^)]+)\)\s*$', degree)
    if m_paren:
        d = m_paren.group(1).strip()
        f = m_paren.group(2).strip()
        if d and f:
            return normalize_degree_name(d), f

    # Pattern 4: "BS Computer Science", "BSc Computer Science", etc.
    m_abbrev = re.match(r'^(B\.?S\.?c?|M\.?S\.?c?|B\.?Tech|M\.?Tech|B\.?E\.?|M\.?E\.?|B\.?A\.?|M\.?A\.?|Ph\.?D\.?)\s+(.+)$', degree, re.IGNORECASE)
    if m_abbrev:
        d = m_abbrev.group(1).strip()
        f = m_abbrev.group(2).strip()
        return normalize_degree_name(d), f

    # Pattern 5: "Bachelor of Science Computer Science" (without 'in')
    m_full = re.match(r'^(Bachelor\s+of\s+\w+|Master\s+of\s+\w+|Associate\s+of\s+\w+)\s+(.+)$', degree, re.IGNORECASE)
    if m_full:
        d = m_full.group(1).strip()
        f = m_full.group(2).strip()
        return normalize_degree_name(d), f

    return normalize_degree_name(degree), field


KNOWN_SECTION_HEADERS = [
    r'PROFESSIONAL\s+SUMMARY', r'SUMMARY', r'PROFILE', r'OBJECTIVE',
    r'EDUCATION', r'ACADEMIC\s+BACKGROUND',
    r'KEY\s+PROJECTS', r'PROJECTS', r'PERSONAL\s+PROJECTS',
    r'WORK\s+EXPERIENCE', r'PROFESSIONAL\s+EXPERIENCE', r'EXPERIENCE', r'EMPLOYMENT',
    r'TECHNICAL\s+SKILLS', r'CORE\s+COMPETENCIES', r'SKILLS',
    r'CERTIFICATIONS', r'CERTIFICATES', r'LICENSES(?:\s*&\s*CERTIFICATIONS)?',
    r'AWARDS(?:\s*&\s*HONORS)?', r'HONORS(?:\s*&\s*AWARDS)?', r'ACHIEVEMENTS', r'KEY\s+ACHIEVEMENTS', r'AWARDS\s*&\s*ACHIEVEMENTS', r'ACCOMPLISHMENTS',
    r'LANGUAGES', r'SPOKEN\s+LANGUAGES',
    r'VOLUNTEER(?:\s*EXPERIENCE)?', r'COMMUNITY\s+SERVICE', r'LEADERSHIP',
    r'PUBLICATIONS', r'REFERENCES'
]

KNOWN_HEADER_PATTERN = '|'.join(KNOWN_SECTION_HEADERS)


def extract_section_raw(text: str, header_regex: str) -> str:
    """
    Extracts the raw body text of a section matching header_regex up to the next known section header.
    """
    if not text:
        return ""
    # Strip embedded hyperlinks block from text before section extraction so no section ever absorbs hyperlink anchors
    clean_text = re.split(r'\n*---+\s*EMBEDDED\s+HYPERLINKS\s+IN\s+RESUME\s*---+', text, flags=re.IGNORECASE)[0]

    is_skills_sec = bool(re.search(r'SKILL', header_regex, re.IGNORECASE))
    if is_skills_sec:
        term_headers = [h for h in KNOWN_SECTION_HEADERS if not any(k in h for k in ['SKILL', 'LANGUAGES'])]
        term_headers.append(r'SPOKEN\s+LANGUAGES')
        term_pattern = '|'.join(term_headers)
        pattern = rf'(?:^|\n)\s*(?:{header_regex})\s*[:\n]+(.*?)(?=\n\s*(?:{term_pattern})\s*[:\n]|\Z)'
    else:
        pattern = rf'(?:^|\n)\s*(?:{header_regex})\s*[:\n]+(.*?)(?=\n\s*(?:{KNOWN_HEADER_PATTERN})\s*[:\n]|\Z)'
    match = re.search(pattern, clean_text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


DATE_RANGE_PATTERN = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})\s*[-–—to]+\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|Present|Current)'


def parse_raw_experience(raw_text: str) -> list[dict]:
    """
    Parses work experience directly from document raw text when LLM omits or drops the section.
    If no work experience section exists (e.g. student/new-grad resume), returns empty list [].
    """
    body = extract_section_raw(
        raw_text,
        r'WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EXPERIENCE|EMPLOYMENT(?:\s+HISTORY)?|WORK\s+HISTORY|INTERNSHIPS|RELEVANT\s+EXPERIENCE|CAREER\s+HISTORY'
    )
    if not body:
        return []

    lines = [line.rstrip() for line in body.split('\n') if line.strip()]
    if not lines:
        return []

    experiences = []
    current_exp = None

    for line in lines:
        line_clean = line.strip()
        if re.match(r'^(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT|INTERNSHIPS|WORK\s+HISTORY)$', line_clean, re.IGNORECASE):
            continue

        is_bullet = bool(re.match(r'^[•\-\*·\d\.\)]\s+', line_clean))
        clean_text = re.sub(r'^[•\-\*·\d\.\)]\s*', '', line_clean).strip()
        date_match = re.search(DATE_RANGE_PATTERN, line_clean, re.IGNORECASE)

        if not is_bullet and date_match:
            if current_exp and (current_exp.get('position') or current_exp.get('company')):
                experiences.append(current_exp)

            start_d = date_match.group(1).strip()
            end_d = date_match.group(2).strip()
            is_curr = bool(re.search(r'Present|Current', end_d, re.IGNORECASE))

            prefix = line_clean[:date_match.start()].strip()
            suffix = line_clean[date_match.end():].strip()
            rem = f"{prefix} {suffix}".strip()
            rem = re.sub(r'\s*[\(\[\|·,]\s*$', '', rem).strip()
            rem = re.sub(r'^\s*[\)\]\|·,]\s*', '', rem).strip()

            position = ""
            company = ""
            location = ""

            loc_m = re.search(r'[·|]\s*([A-Za-z\s]+(?:,\s*[A-Za-z]{2,})?|Remote)$', rem, re.IGNORECASE)
            if loc_m:
                location = loc_m.group(1).strip()
                rem = rem[:loc_m.start()].strip()

            parts = [p.strip() for p in re.split(r'\s*[-–—|@]\s*|\s+at\s+', rem) if p.strip()]
            if len(parts) >= 2:
                p1, p2 = parts[0], parts[1]
                pos_keywords = ['engineer', 'developer', 'intern', 'manager', 'lead', 'analyst', 'designer', 'architect', 'consultant', 'associate', 'specialist', 'officer', 'assistant']
                if any(k in p1.lower() for k in pos_keywords):
                    position = p1
                    company = p2
                else:
                    company = p1
                    position = p2
                if len(parts) > 2 and not location:
                    location = parts[2]
            elif len(parts) == 1:
                position = parts[0]
                company = ""

            current_exp = {
                "id": f"exp_{uuid.uuid4().hex[:8]}",
                "position": position,
                "company": company,
                "location": location,
                "start_date": start_d,
                "end_date": "Present" if is_curr else end_d,
                "is_current": is_curr,
                "achievements": []
            }
        elif is_bullet:
            if current_exp:
                current_exp["achievements"].append(clean_text)
            else:
                current_exp = {
                    "id": f"exp_{uuid.uuid4().hex[:8]}",
                    "position": "Professional Role",
                    "company": "",
                    "location": "",
                    "start_date": "",
                    "end_date": "",
                    "is_current": False,
                    "achievements": [clean_text]
                }
        else:
            if current_exp and not current_exp["achievements"]:
                if not current_exp["company"]:
                    current_exp["company"] = line_clean
                elif not current_exp["position"]:
                    current_exp["position"] = line_clean
            elif current_exp and current_exp["achievements"]:
                current_exp["achievements"].append(clean_text)

    if current_exp and (current_exp.get('position') or current_exp.get('company') or current_exp.get('achievements')):
        experiences.append(current_exp)

    return experiences



MONTH_NAMES_PATTERN = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'

DATE_TOKEN_RE = re.compile(
    rf'^(?:'
    rf'\d{{1,2}}\s+{MONTH_NAMES_PATTERN}(?:\s+\d{{2,4}})?'
    rf'|{MONTH_NAMES_PATTERN}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{2,4}})?'
    rf'|{MONTH_NAMES_PATTERN}(?:\s+\d{{2,4}})?'
    rf'|\d{{1,2}}[\/\.-]\d{{1,2}}[\/\.-]\d{{2,4}}'
    rf'|\d{{1,2}}[\/\.-]\d{{2,4}}'
    rf'|(?:19|20)\d{{2}}'
    rf'|present|ongoing'
    rf')$',
    re.IGNORECASE
)

TRAILING_DATE_RE = re.compile(
    rf'(?:[\s\(\[\-–—|,]+)('
    rf'\d{{1,2}}\s+{MONTH_NAMES_PATTERN}(?:\s+\d{{2,4}})?'
    rf'|{MONTH_NAMES_PATTERN}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,?\s*\d{{2,4}})?'
    rf'|{MONTH_NAMES_PATTERN}(?:\s+\d{{2,4}})?'
    rf'|\d{{1,2}}[\/\.-]\d{{1,2}}[\/\.-]\d{{2,4}}'
    rf'|\d{{1,2}}[\/\.-]\d{{2,4}}'
    rf'|(?:19|20)\d{{2}}'
    rf')[\)\]]?$',
    re.IGNORECASE
)


def parse_raw_certifications(raw_text: str) -> list[dict]:
    """
    Parses certifications directly from document raw text when LLM omits or drops them.
    Robustly handles dates on separate lines (e.g. "bbb \n 9 sept") or inline (e.g. "bbb  9 sept").
    Also recovers credential verification links from embedded hyperlinks.
    """
    body = extract_section_raw(
        raw_text,
        r'CERTIFICATIONS|CERTIFICATES|LICENSES(?:\s*&\s*CERTIFICATIONS)?|COURSES(?:\s*&\s*CERTIFICATIONS)?'
    )
    if not body:
        return []
    certs = []
    seen = set()
    raw_lines = [line.strip() for line in body.split('\n') if line.strip()]
    lines = []
    for l in raw_lines:
        l_clean = re.sub(r'^[•\-\*·\d\.\)]\s*', '', l).strip()
        if not l_clean:
            continue
        if l_clean.upper() in ('CERTIFICATIONS', 'CERTIFICATES', 'LICENSES', 'COURSES', 'LANGUAGES', 'SPOKEN LANGUAGES'):
            continue
        if l_clean.startswith("Anchor:") or "Target URL:" in l_clean or l_clean.startswith("--"):
            continue
        lines.append(l_clean)

    KNOWN_ISSUERS = {'deloitte', 'worldclass', 'coursera', 'udemy', 'google', 'aws', 'amazon', 'microsoft', 'ibm', 'meta', 'cisco', 'oracle', 'university', 'college', 'school', 'academy', 'institute', 'foundation', 'edx', 'linkedin learning', 'stanford'}

    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1

        # If this entire line is just a date token (e.g. "9 sept", "sept", "September 8, 2026"):
        if DATE_TOKEN_RE.match(line):
            if certs and not certs[-1].get("date"):
                certs[-1]["date"] = line
            continue

        c_name = line
        c_issuer = ""
        c_date = ""

        # Filter out label words like "Credential", "Certificate", "Verify", "View", etc.
        if c_name.lower() in ("credential", "credentials", "verify", "verification", "view credential", "certificate", "certificates", "view certificate", "link", "url", "view"):
            continue

        # Check for inline trailing date (e.g. "bbb   9 sept" or "bbb (9 sept)")
        m_trailing = TRAILING_DATE_RE.search(c_name)
        if m_trailing:
            c_date = m_trailing.group(1).strip()
            c_name = c_name[:m_trailing.start()].strip().rstrip("-–—|([{ ")

        # Check for issuer separated by - or |
        m_dash = re.match(r'^(.*?)\s*[-–—|]\s*(.*?)(?:\s*[\(\[]([^\)\]]+)[\)\]])?$', c_name)
        if m_dash and m_dash.group(1).strip() and m_dash.group(2).strip():
            c_name = m_dash.group(1).strip()
            c_issuer = m_dash.group(2).strip()
            if not c_date and m_dash.group(3):
                c_date = m_dash.group(3).strip()

        # Check if this line is actually an issuer for the preceding certificate
        next_is_date = (i < len(lines) and bool(DATE_TOKEN_RE.match(lines[i])))
        is_issuer_word = any(k in c_name.lower() for k in KNOWN_ISSUERS)
        if certs and not certs[-1]["issuer"] and (next_is_date or is_issuer_word):
            certs[-1]["issuer"] = c_name
            if c_date and not certs[-1]["date"]:
                certs[-1]["date"] = c_date
            continue

        # Reject if c_name is empty or is purely a date token
        if not c_name or DATE_TOKEN_RE.match(c_name):
            if certs and not certs[-1].get("date") and c_name:
                certs[-1]["date"] = c_name
            continue

        if c_name.lower() not in seen:
            seen.add(c_name.lower())
            certs.append({
                "id": f"cert_{uuid.uuid4().hex[:8]}",
                "name": c_name,
                "issuer": c_issuer,
                "date": c_date,
                "expiry_date": "",
                "credential_url": ""
            })

    # Associate candidate credential URLs from raw_text
    embedded_parsed = extract_hyperlinks_from_text(raw_text)
    cert_urls = []
    seen_urls = set()
    for item in embedded_parsed:
        u = item["uri"]
        if u in seen_urls:
            continue
        if any(d in u.lower() for d in ["drive.google.com", "credly.com", "coursera.org", "udemy.com", "badgr", "credential", "certificate", "verify"]) or \
           any(w in item["anchor"].lower() for w in ["credential", "certificate", "verify", "view", "cert"]) or \
           any(w in item["context"].lower() for w in ["credential", "certificate", "deloitte", "worldclass", "coursera"]):
            seen_urls.add(u)
            cert_urls.append((item["anchor"], item["context"], u))

    assigned_urls = set()
    for idx, c in enumerate(certs):
        if not c.get("credential_url"):
            matched_u = ""
            c_name_low = c["name"].lower()
            for a, ctx, u in cert_urls:
                if u not in assigned_urls and c_name_low and (c_name_low in ctx.lower() or c_name_low in a.lower()):
                    matched_u = u
                    break
            if not matched_u:
                unassigned = [u for a, ctx, u in cert_urls if u not in assigned_urls]
                if unassigned:
                    matched_u = unassigned[0]
                elif idx < len(cert_urls):
                    matched_u = cert_urls[idx][2]
            if matched_u:
                c["credential_url"] = matched_u
                assigned_urls.add(matched_u)

    return certs


def parse_raw_awards(raw_text: str) -> list[dict]:
    """
    Parses awards / achievements directly from document raw text.
    """
    body = extract_section_raw(
        raw_text,
        r'ACHIEVEMENTS|KEY\s+ACHIEVEMENTS|AWARDS(?:\s*&\s*HONORS)?|HONORS(?:\s*&\s*AWARDS)?|AWARDS\s*&\s*ACHIEVEMENTS|ACCOMPLISHMENTS'
    )
    if not body:
        return []
    awards = []
    seen = set()
    for line in body.split('\n'):
        l_clean = re.sub(r'^[•\-\*·\d\.\)]\s*', '', line).strip()
        if not l_clean or l_clean.upper() in ('AWARDS', 'ACHIEVEMENTS', 'HONORS', 'KEY ACHIEVEMENTS', 'ACCOMPLISHMENTS'):
            continue

        a_title = l_clean
        a_issuer = ""
        a_date = ""

        m_trailing = TRAILING_DATE_RE.search(a_title)
        if m_trailing:
            a_date = m_trailing.group(1).strip()
            a_title = a_title[:m_trailing.start()].strip().rstrip("-–—|([{ ")

        m_dash = re.match(r'^(.*?)\s*[-–—|]\s*(.*?)(?:\s*[\(\[]([^\)\]]+)[\)\]])?$', a_title)
        if m_dash and m_dash.group(1).strip() and m_dash.group(2).strip():
            a_title = m_dash.group(1).strip()
            a_issuer = m_dash.group(2).strip()
            if not a_date and m_dash.group(3):
                a_date = m_dash.group(3).strip()

        if a_title and a_title.lower() not in seen:
            seen.add(a_title.lower())
            awards.append({
                "id": f"award_{uuid.uuid4().hex[:8]}",
                "title": a_title,
                "issuer": a_issuer,
                "date": a_date,
                "description": ""
            })
    return awards


def parse_raw_languages(raw_text: str) -> list[dict]:
    """
    Parses spoken languages directly from document raw text.
    Handles horizontal/side-by-side languages (e.g. "English (Fluent) Urdu (Fluent) Arabic (Beginner)")
    as well as comma/tab-separated lists.
    Filters out technical programming languages (e.g. Python, SQL).
    """
    body = extract_section_raw(
        raw_text,
        r'SPOKEN\s+LANGUAGES|LANGUAGES|LANGUAGE\s+SKILLS|LANGUAGE\s+PROFICIENCY'
    )
    if not body:
        return []
    
    prog_langs = {'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'c', 'ruby', 'go', 'rust', 'php', 'swift', 'kotlin', 'sql', 'html', 'css', 'r', 'matlab', 'scala', 'dart', 'bash', 'shell', 'docker', 'react'}
    langs = []
    seen = set()
    parts = []

    for line in body.split('\n'):
        line_s = line.strip()
        if not line_s or line_s.upper() in ('LANGUAGES', 'LANGUAGE PROFICIENCY', 'SPOKEN LANGUAGES'):
            continue
        # Split line into parts by comma, pipe, tab, multiple spaces, or right after closing parenthesis followed by space and letter
        # e.g. "English (Fluent)   Urdu (Fluent)   Arabic (Beginner)"
        split_items = re.split(r'[,|•·\/\t]|\s{2,}|\s*(?<=\))\s+(?=[A-Za-z])', line_s)
        for it in split_items:
            it_clean = it.strip()
            if it_clean:
                parts.append(it_clean)

    for p in parts:
        p_clean = re.sub(r'^[•\-\*·\d\.\)]\s*', '', p).strip()
        if not p_clean:
            continue
        m = re.match(r'^(.*?)\s*[\(\-–:]\s*([^\)]+)[\)]?$', p_clean)
        if m and m.group(1).strip() and m.group(2).strip():
            name = m.group(1).strip()
            fluency = m.group(2).strip()
        else:
            name = p_clean
            fluency = ""

        # Filter out programming languages or category headers
        if name.lower() in prog_langs or ":" in name or any(k in name.lower() for k in ["framework", "tool", "library"]):
            continue

        if name and name.lower() not in seen:
            seen.add(name.lower())
            langs.append({
                "id": f"lang_{uuid.uuid4().hex[:8]}",
                "name": name,
                "fluency": fluency
            })
    return langs


def extract_hyperlinks_from_text(text: str) -> list[dict]:
    """Robustly extracts embedded hyperlinks (anchor, context, uri) from formatted resume text."""
    links = []
    if not text or "--- EMBEDDED HYPERLINKS IN RESUME ---" not in text:
        return links
    block = text.split("--- EMBEDDED HYPERLINKS IN RESUME ---", 1)[1]
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("- Anchor:"):
            continue
        url_match = re.search(r'->\s*Target URL:\s*(\S+)', line)
        if not url_match:
            continue
        uri = url_match.group(1).strip()
        
        anchor = ""
        anchor_match = re.search(r"- Anchor:\s*'([^']*)'", line)
        if anchor_match:
            anchor = anchor_match.group(1).strip()
        
        context = ""
        ctx_match = re.search(r"\(Context:\s*'([^']*)'\)", line)
        if ctx_match:
            context = ctx_match.group(1).strip()
            
        links.append({"anchor": anchor, "context": context, "uri": uri})
    return links


def extract_contact_info_deterministic(text: str) -> dict:
    """
    Blazing fast, zero-dependency regex and rule-based extractor for core contact details.
    Runs in ~2ms. Used for instant pre-population of the resume template.
    """
    info = {
        "first_name": "",
        "last_name": "",
        "professional_title": "",
        "email": "",
        "phone": "",
        "address": "",
        "linkedin": "",
        "github": "",
        "portfolio": "",
        "website": "",
    }
    if not text:
        return info

    # Pre-heal any split lines in text
    text = heal_split_tokens(text)

    # 1. Email
    email_m = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_m:
        info["email"] = email_m.group(0).strip()

    # 2. Phone (supports international +, dashes, spaces, and 7-15 digit numbers)
    # Strip emails first so digits inside email addresses don't hijack phone detection
    text_no_emails = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '', text[:600])
    phone_m = re.search(r'(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}\b|\b\d{8,14}\b', text_no_emails)
    if phone_m:
        val = phone_m.group(0).strip()
        if len(re.sub(r'\D', '', val)) >= 7:
            info["phone"] = re.sub(r'\s+', ' ', val).strip()

    # 3. URLs & Links in raw text lines
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for l in lines[:25]:
        if "linkedin.com" in l.lower() and not info["linkedin"]:
            m = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/[A-Za-z0-9_.-]+(?:\/)?', l, re.I)
            if m:
                info["linkedin"] = m.group(0) if m.group(0).startswith("http") else f"https://{m.group(0)}"
        if "github.com" in l.lower() and not info["github"]:
            m = re.search(r'(?:https?:\/\/)?(?:www\.)?github\.com\/[A-Za-z0-9_.-]+(?:\/)?', l, re.I)
            if m:
                info["github"] = m.group(0) if m.group(0).startswith("http") else f"https://{m.group(0)}"
        if any(w in l.lower() for w in ("portfolio:", "website:", "site:", "web:")):
            m = re.search(r'(?:https?:\/\/)?([A-Za-z0-9_.-]+\.[A-Za-z]{2,})(?:\/[^\s]*)?', l, re.I)
            if m:
                val = m.group(0) if m.group(0).startswith("http") else f"https://{m.group(0)}"
                if "portfolio" in l.lower() and not info["portfolio"]:
                    info["portfolio"] = val
                elif not info["website"]:
                    info["website"] = val

    # Search for LinkedIn anywhere in raw text
    if not info["linkedin"]:
        m_li = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/[A-Za-z0-9_.-]+(?:\/)?', text, re.I)
        if not m_li:
            m_li = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/[A-Za-z0-9_.-]+(?:\/)?', text, re.I)
        if not m_li:
            m_li = re.search(r'\b(?:linkedin\s*[:|•\-–—]\s*|in\/)([a-zA-Z0-9_\-\.]{3,})\b', text, re.I)
            if m_li and m_li.group(1).lower() not in ("linkedin", "profile", "com", "www"):
                slug = m_li.group(1).strip()
                info["linkedin"] = f"https://www.linkedin.com/in/{slug}"
        if m_li and not info["linkedin"]:
            val = m_li.group(0).strip()
            info["linkedin"] = val if val.startswith("http") else f"https://{val}"

    # 4. Embedded Hyperlinks
    embedded_parsed = extract_hyperlinks_from_text(text)
    for item in embedded_parsed:
        uri = item["uri"]
        anchor = item["anchor"]
        ctx = item["context"]
        
        # Check if anchor is itself a full URL (e.g. user typed github.com/user or linkedin.com/in/...)
        effective_url = uri
        if "linkedin.com" in anchor.lower():
            effective_url = anchor if anchor.startswith("http") else f"https://{anchor}"
        elif "github.com" in anchor.lower():
            effective_url = anchor if anchor.startswith("http") else f"https://{anchor}"
        elif any(d in anchor.lower() for d in [".vercel.app", ".github.io", ".netlify.app", ".dev", ".me", ".pages.dev"]):
            effective_url = anchor if anchor.startswith("http") else f"https://{anchor}"

        # Helper to check for dummy URLs like https://github/
        def is_dummy_candidate(u: str) -> bool:
            clean = u.strip().lower()
            if clean in ("https://linkedin/", "https://linkedin", "https://github/", "https://github", "https://live/", "https://live"):
                return True
            try:
                from urllib.parse import urlparse
                p = urlparse(clean if "://" in clean else f"https://{clean}")
                net = p.netloc or p.path.split('/')[0]
                if "." not in net:
                    return True
            except Exception:
                pass
            return False

        if effective_url.startswith("mailto:") or effective_url.startswith("tel:"):
            continue

        a_low = anchor.strip().lower()

        # LinkedIn detection
        if ("linkedin.com" in effective_url.lower() or "linkedin" in a_low or "linkedin.com" in uri.lower()) and not info["linkedin"]:
            target_li = effective_url if "linkedin.com" in effective_url.lower() else uri
            if "linkedin.com" in target_li.lower():
                info["linkedin"] = target_li if target_li.startswith("http") else f"https://{target_li}"

        # GitHub detection (user profile)
        if ("github.com" in effective_url.lower() or "github" in a_low) and not info["github"]:
            target_gh = effective_url if "github.com" in effective_url.lower() else uri
            if "github.com" in target_gh.lower():
                segs = [s for s in target_gh.split('/') if s and s not in ('http:', 'https:', 'github.com', 'www.github.com')]
                if len(segs) <= 1:
                    info["github"] = target_gh

        # Portfolio detection
        if ("portfolio" in a_low or a_low in ("portfolio", "my portfolio", "portfolio site")) and not info["portfolio"] and not is_dummy_candidate(effective_url):
            if "linkedin.com" not in effective_url.lower() and "github.com" not in effective_url.lower():
                info["portfolio"] = effective_url

        # Website detection
        if ("website" in a_low or a_low in ("website", "my website", "personal website", "site", "web", "blog")) and not info["website"] and not is_dummy_candidate(effective_url):
            if "linkedin.com" not in effective_url.lower() and "github.com" not in effective_url.lower():
                info["website"] = effective_url

    # Fallback for portfolio from personal domain link if still unset
    if not info["portfolio"]:
        for item in embedded_parsed:
            u = item["uri"]
            if any(d in u.lower() for d in [".vercel.app", ".github.io", ".netlify.app", ".pages.dev", ".me", ".dev"]):
                if "github.com" not in u.lower() and "linkedin.com" not in u.lower() and not u.startswith("mailto:") and not u.startswith("tel:"):
                    info["portfolio"] = u
                    break

    # General GitHub profile fallback if only repo links existed in embedded links
    if not info["github"]:
        for item in embedded_parsed:
            u = item["uri"]
            if "github.com" in u.lower():
                segs = [s for s in u.split('/') if s and s not in ('http:', 'https:', 'github.com', 'www.github.com')]
                if segs:
                    info["github"] = f"https://github.com/{segs[0]}"
                    break

    # 5. Name and Title extraction from header lines (first 1-6 lines)
    header_candidates = []
    for l in lines[:6]:
        if any(w in l.lower() for w in ["@", "http", "curriculum", "resume", "experience", "education", "summary", "skills"]):
            continue
        cleaned = re.sub(r'[^A-Za-z\s\.\-]', '', l).strip()
        parts = cleaned.split()
        if 2 <= len(parts) <= 4 and all(len(p) > 1 for p in parts):
            header_candidates.append(cleaned)

    if header_candidates:
        name_parts = header_candidates[0].split()
        info["first_name"] = name_parts[0]
        info["last_name"] = " ".join(name_parts[1:])
        if len(header_candidates) > 1:
            info["professional_title"] = header_candidates[1]

    # 6. Location / Address (single line, e.g. "City, State", "City, Country", or "Remote")
    loc_m = re.search(r'\b([A-Za-z ]{2,30},\s*(?:[A-Za-z ]{2,30}))', text[:500])
    if loc_m:
        cand = loc_m.group(1).strip()
        if not any(w in cand.lower() for w in ["university", "college", "school", "company", "inc", "ltd"]):
            info["address"] = cand

    # 7. Fallback for LinkedIn if label present in header lines but no embedded link
    if not info["linkedin"] and any(l.strip().lower() in ("linkedin", "linkedin:", "linkedin profile") for l in lines[:25]):
        fn = (info.get("first_name") or "").strip().lower()
        ln = (info.get("last_name") or "").strip().lower()
        if fn and ln:
            info["linkedin"] = f"https://www.linkedin.com/in/{fn}-{ln}"
        elif info.get("github"):
            gh_slug = info["github"].rstrip("/").split("/")[-1]
            if gh_slug and gh_slug.lower() not in ("github", "com"):
                info["linkedin"] = f"https://www.linkedin.com/in/{gh_slug}"

    return info


def parse_raw_education(raw_text: str) -> list[dict]:
    """Parses education entries with degree and institution directly from raw text."""
    body = extract_section_raw(
        raw_text,
        r'EDUCATION|ACADEMIC\s+BACKGROUND|ACADEMIC\s+QUALIFICATIONS|ACADEMICS|STUDIES'
    )
    if not body:
        return []
    lines = [line.rstrip() for line in body.split('\n') if line.strip()]
    if not lines:
        return []
    education = []
    cur_edu = None

    date_range_re = re.compile(r'([A-Za-z]{3,}\s+\d{4}|\b\d{4})\s*[-–—·~to]+\s*([A-Za-z]{3,}\s+\d{4}|\b\d{4}|Present|Current|Expected)', re.I)
    gpa_re = re.compile(r'\b(?:\d\.\d{1,2}\s*\/\s*\d\.\d{1,2}|GPA\s*[:=]?\s*\d\.\d{1,2})\b', re.I)

    for line in lines:
        line_clean = line.strip()
        if re.match(r'^(?:EDUCATION|ACADEMICS|STUDIES)$', line_clean, re.IGNORECASE):
            continue
        is_inst = any(k in line_clean.lower() for k in ["university", "college", "institute", "school", "academy", "polytechnic"])
        is_deg = any(k in line_clean.lower() for k in ["bachelor", "master", "phd", "doctor", "associate", "b.s", "m.s", "b.a", "m.a", "b.tech", "m.tech", "bba", "mba", "degree", "diploma"])

        m_range = date_range_re.search(line_clean)
        m_gpa = gpa_re.search(line_clean)

        # Standalone date or GPA line
        if m_range and len(line_clean) <= 35:
            if cur_edu:
                cur_edu["start_date"] = m_range.group(1).strip()
                cur_edu["end_date"] = m_range.group(2).strip()
                if any(w in m_range.group(2).lower() for w in ["present", "current", "expected"]):
                    cur_edu["is_current"] = True
            continue

        if m_gpa and len(line_clean) <= 25:
            if cur_edu:
                cur_edu["grade"] = m_gpa.group(0).strip()
            continue

        if is_deg:
            # If current education already has a degree, push and start a new one
            if cur_edu and cur_edu.get("degree"):
                education.append(cur_edu)
                cur_edu = None

            deg, field = split_degree_and_field(line_clean, "")
            if not cur_edu:
                cur_edu = {
                    "id": f"edu_{uuid.uuid4().hex[:8]}",
                    "degree": deg or line_clean,
                    "field_of_study": field,
                    "institution": "",
                    "location": "",
                    "start_date": "",
                    "end_date": "",
                    "is_current": False,
                    "grade": ""
                }
            else:
                cur_edu["degree"] = deg or line_clean
                cur_edu["field_of_study"] = field
            continue

        if is_inst:
            # If current education already has an institution, push and start a new one
            if cur_edu and cur_edu.get("institution"):
                education.append(cur_edu)
                cur_edu = None

            inst_name = line_clean
            loc = ""
            for sep in [" · ", " • ", " - ", " – ", " — ", ", "]:
                if sep in line_clean:
                    parts = line_clean.split(sep, 1)
                    inst_name = parts[0].strip()
                    loc = parts[1].strip()
                    break

            if not cur_edu:
                cur_edu = {
                    "id": f"edu_{uuid.uuid4().hex[:8]}",
                    "degree": "",
                    "field_of_study": "",
                    "institution": inst_name,
                    "location": loc,
                    "start_date": "",
                    "end_date": "",
                    "is_current": False,
                    "grade": ""
                }
            else:
                cur_edu["institution"] = inst_name
                if loc:
                    cur_edu["location"] = loc
            continue

        if cur_edu:
            if m_range and not cur_edu.get("end_date"):
                cur_edu["start_date"] = m_range.group(1).strip()
                cur_edu["end_date"] = m_range.group(2).strip()
                if any(w in m_range.group(2).lower() for w in ["present", "current", "expected"]):
                    cur_edu["is_current"] = True
            elif m_gpa and not cur_edu.get("grade"):
                cur_edu["grade"] = m_gpa.group(0).strip()

    if cur_edu and (cur_edu.get("degree") or cur_edu.get("institution")):
        education.append(cur_edu)
    return education


def parse_raw_projects(raw_text: str) -> list[dict]:
    """Parses project entries with title, technologies, and bullet highlights."""
    body = extract_section_raw(
        raw_text,
        r'PROJECTS|PERSONAL\s+PROJECTS|ACADEMIC\s+PROJECTS|KEY\s+PROJECTS|PORTFOLIO\s+PROJECTS'
    )
    if not body:
        return []
    lines = [line.rstrip() for line in body.split('\n') if line.strip()]
    if not lines:
        return []

    def is_proj_date(s: str) -> bool:
        return bool(DATE_TOKEN_RE.match(s) or (re.search(r'\b(?:19|20)\d{2}\b', s) and any(m in s.lower() for m in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec','present','current','-','–','—'])))

    def is_proj_link(s: str) -> bool:
        return s.lower() in ('github', 'live', 'demo', 'code', 'repo', 'link', 'url', 'view', 'preview', 'site', 'website', 'live demo')

    def is_action_verb(s: str) -> bool:
        return bool(re.match(r'^(?:built|developed|created|engineered|designed|implemented|trained|architected|leading|managed|optimized|fine-tuned|deployed|maintained|spearheaded|utilized|authored|formulated)\b', s, re.I))

    common_tools = {'git', 'github', 'c', 'c++', 'python', 'java', 'sql', 'javascript', 'html', 'css', 'oop', 'crud', 'ai algorithms', 'docker', 'react', 'node.js', 'next.js'}

    projects = []
    cur_proj = None
    i = 0

    while i < len(lines):
        line = lines[i]
        i += 1
        line_clean = line.strip()
        if re.match(r'^(?:PROJECTS|PERSONAL\s+PROJECTS|ACADEMIC\s+PROJECTS|KEY\s+PROJECTS)$', line_clean, re.IGNORECASE):
            continue

        is_bullet = bool(re.match(r'^[•\-\*·\d\.\)]\s+', line_clean))
        clean_text = re.sub(r'^[•\-\*·\d\.\)]\s*', '', line_clean).strip()
        if not clean_text:
            continue

        # If date line
        if is_proj_date(clean_text):
            if cur_proj and not cur_proj.get("date"):
                cur_proj["date"] = clean_text
            continue

        # If link word
        if is_proj_link(clean_text):
            if cur_proj and not cur_proj.get("description"):
                continue
            if cur_proj and (cur_proj.get("description") or cur_proj.get("highlights")) and clean_text.lower() in common_tools:
                cur_proj["technologies"].append(clean_text)
            continue

        # If explicit technologies line
        if re.match(r'^(?:technologies|tech\s+stack|tools|built\s+with)[:\s]+', clean_text, re.I):
            if cur_proj:
                rest = re.sub(r'^(?:technologies|tech\s+stack|tools|built\s+with)[:\s]+', '', clean_text, flags=re.I)
                cur_proj["technologies"].extend([x.strip() for x in re.split(r'[,;|•/]', rest) if x.strip()])
            continue

        # Lookahead: if next line is a date or link, clean_text is definitely a new project title!
        next_is_meta = (i < len(lines) and (is_proj_date(lines[i].strip()) or (is_proj_link(lines[i].strip()) and lines[i].strip().lower() not in ('git', 'github', 'c'))))
        if next_is_meta:
            if cur_proj and cur_proj.get('title'):
                projects.append(cur_proj)
            cur_proj = {
                "id": f"proj_{uuid.uuid4().hex[:8]}",
                "title": clean_text,
                "date": "",
                "description": "",
                "technologies": [],
                "github_url": "",
                "live_url": "",
                "highlights": []
            }
            continue

        # If description or highlight bullet
        if is_bullet or len(clean_text) > 40 or clean_text.endswith('.') or is_action_verb(clean_text):
            if cur_proj:
                if not cur_proj["description"]:
                    cur_proj["description"] = clean_text
                else:
                    cur_proj["highlights"].append(clean_text)
                continue

        # If trailing skill or tool tag under an existing project
        if cur_proj and (cur_proj.get("highlights") or cur_proj.get("description")) and (clean_text.lower() in common_tools or is_valid_skill_name(clean_text) and len(clean_text.split()) <= 3):
            cur_proj["technologies"].append(clean_text)
            continue

        # New project fallback
        if cur_proj and cur_proj.get('title'):
            projects.append(cur_proj)
        cur_proj = {
            "id": f"proj_{uuid.uuid4().hex[:8]}",
            "title": clean_text,
            "date": "",
            "description": "",
            "technologies": [],
            "github_url": "",
            "live_url": "",
            "highlights": []
        }

    if cur_proj and cur_proj.get('title') and (cur_proj.get('description') or cur_proj.get('highlights') or cur_proj.get('date')):
        projects.append(cur_proj)

    return projects


def parse_resume_deterministic(text: str, photo: Optional[str] = None, detected_font: Optional[str] = None) -> dict:
    """
    High-speed, offline deterministic parser that structures raw resume text
    in <50ms without external API dependencies.
    """
    contact = extract_contact_info_deterministic(text)
    skill_to_cat, cat_headers, raw_skills = build_skill_category_map(text)
    
    skills = []
    seen_skills = set()
    for s_lower, (orig_name, s_cat) in raw_skills.items():
        if s_lower not in seen_skills and is_valid_skill_name(orig_name):
            seen_skills.add(s_lower)
            skills.append({
                "id": f"skill_{uuid.uuid4().hex[:8]}",
                "name": orig_name,
                "category": normalize_skill_category(s_cat),
                "proficiency": 5
            })

    experience = parse_raw_experience(text)
    education = parse_raw_education(text)
    projects = parse_raw_projects(text)
    certifications = parse_raw_certifications(text)
    awards = parse_raw_awards(text)
    languages = parse_raw_languages(text)

    summary = ""
    summary_raw = extract_section_raw(text, r'SUMMARY|PROFILE|ABOUT\s+ME|PROFESSIONAL\s+SUMMARY|OBJECTIVE')
    if summary_raw:
        paras = [p.strip() for p in summary_raw.split('\n\n') if p.strip()]
        if paras:
            summary = paras[0].replace('\n', ' ')

    result = {
        **contact,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "projects": projects,
        "certifications": certifications,
        "awards": awards,
        "languages": languages,
        "volunteer": []
    }
    
    result = post_process_json(result, raw_text=text)
    if photo:
        result["photo"] = photo
    if detected_font:
        if not result.get("theme_settings"):
            result["theme_settings"] = {}
        result["theme_settings"]["font_family"] = detected_font
        
    return clean_dict(result)


def post_process_json(parsed_json, raw_text: str = None):
    if not isinstance(parsed_json, dict):
        return parsed_json
        
    skill_to_cat = {}
    raw_skills = {}
    if raw_text:
        skill_to_cat, _, raw_skills = build_skill_category_map(raw_text)

    # Map alternative section names from LLM
    if "certificates" in parsed_json and "certifications" not in parsed_json:
        parsed_json["certifications"] = parsed_json.pop("certificates")

    if "work_experience" in parsed_json and "experience" not in parsed_json:
        parsed_json["experience"] = parsed_json.pop("work_experience")

    if "achievements" in parsed_json and isinstance(parsed_json["achievements"], list):
        if not parsed_json.get("awards"):
            parsed_json["awards"] = parsed_json.pop("achievements")
        else:
            parsed_json["awards"].extend(parsed_json.pop("achievements"))

    # 1. Properly categorize all skills, normalize categories, assign unique IDs, and deduplicate
    seen_skills = set()
    clean_skills = []
    if "skills" in parsed_json and isinstance(parsed_json["skills"], list):
        for skill in parsed_json["skills"]:
            if isinstance(skill, dict):
                s_name = str(skill.get("name", "")).strip()
                if not s_name or not is_valid_skill_name(s_name):
                    continue
                s_key = s_name.lower()
                if s_key in seen_skills:
                    continue
                seen_skills.add(s_key)

                cat = skill.get("category")
                if cat:
                    cat = str(cat).strip().rstrip(":")
                
                # If mapped from CV text, use the exact CV category header
                if s_key in skill_to_cat:
                    cat = skill_to_cat[s_key]
                elif not cat or cat.lower() in ("technical", "skills", "general"):
                    cat = skill_to_cat.get(s_key) or cat or "Technical Skills"
                
                cat = normalize_skill_category(cat)
                skill["name"] = s_name
                skill["category"] = cat
                if not skill.get("id"):
                    skill["id"] = f"skill_{uuid.uuid4().hex[:8]}"
                clean_skills.append(skill)

    # Merge any skills from raw_text that LLM missed (e.g. Wireshark, Google Colab, Replit, GitLab CI/CD)
    if raw_skills:
        for s_lower, (orig_name, s_cat) in raw_skills.items():
            if s_lower not in seen_skills and is_valid_skill_name(orig_name):
                seen_skills.add(s_lower)
                clean_skills.append({
                    "id": f"skill_{uuid.uuid4().hex[:8]}",
                    "name": orig_name,
                    "category": normalize_skill_category(s_cat),
                    "proficiency": 5
                })

    # Harvest skills from project tools/technologies so project-level skills are never skipped
    proj_list_pre = parsed_json.get("projects") if isinstance(parsed_json.get("projects"), list) else []
    for proj in proj_list_pre:
        if isinstance(proj, dict):
            techs = proj.get("technologies") or proj.get("tools") or []
            if isinstance(techs, str):
                techs = [t.strip() for t in re.split(r'[,;|•·\t]|\s+/\s+|\s{2,}', techs) if t.strip()]
            elif not isinstance(techs, list):
                techs = []
            for t in techs:
                t_str = str(t).strip()
                if is_valid_skill_name(t_str) and t_str.lower() not in seen_skills:
                    seen_skills.add(t_str.lower())
                    clean_skills.append({
                        "id": f"skill_{uuid.uuid4().hex[:8]}",
                        "name": t_str,
                        "category": normalize_skill_category(skill_to_cat.get(t_str.lower()) or "Technical Skills"),
                        "proficiency": 5
                    })

    if clean_skills:
        parsed_json["skills"] = clean_skills

    # 2. Clean, filter non-dicts, and assign unique IDs to projects
    if "projects" in parsed_json and isinstance(parsed_json["projects"], list):
        clean_projs = []
        for proj in parsed_json["projects"]:
            if isinstance(proj, dict):
                if not proj.get("title") and proj.get("name"):
                    proj["title"] = proj["name"]
                if not proj.get("id"):
                    proj["id"] = f"proj_{uuid.uuid4().hex[:8]}"
                clean_projs.append(proj)
        parsed_json["projects"] = clean_projs

    # Ensure list sections only contain dictionaries
    for sec_name in ["experience", "education", "certifications", "awards", "volunteer"]:
        if sec_name in parsed_json and isinstance(parsed_json[sec_name], list):
            parsed_json[sec_name] = [item for item in parsed_json[sec_name] if isinstance(item, dict)]

    # 3. Clean education entries, separate degree and field of study, and assign unique IDs
    if "education" in parsed_json and isinstance(parsed_json["education"], list):
        for edu in parsed_json["education"]:
            if isinstance(edu, dict):
                if not edu.get("id"):
                    edu["id"] = f"edu_{uuid.uuid4().hex[:8]}"
                d = edu.get("degree", "")
                f = edu.get("field_of_study", "")
                new_d, new_f = split_degree_and_field(d, f)
                edu["degree"] = new_d
                edu["field_of_study"] = new_f

    # 4. Purge "None" from experience, assign IDs, and move President/Club roles to volunteer
    exp_list = parsed_json.get("experience")
    if isinstance(exp_list, list) and len(exp_list) > 0:
        real_exp = []
        if "volunteer" not in parsed_json or not isinstance(parsed_json["volunteer"], list):
            parsed_json["volunteer"] = []
            
        for exp in exp_list:
            if not isinstance(exp, dict):
                continue
                
            title = str(exp.get("position", "")).lower()
            company = str(exp.get("company", "")).lower()
            
            if title in ("none", "", "n/a", "null") and company in ("none", "", "n/a", "null"):
                continue
                
            if "president" in title or "club" in company or "society" in company or "volunteer" in title or "lounge" in company:
                parsed_json["volunteer"].append({
                    "id": f"vol_{uuid.uuid4().hex[:8]}",
                    "organization": exp.get("company", ""),
                    "role": exp.get("position", ""),
                    "location": exp.get("location", ""),
                    "start_date": exp.get("start_date", ""),
                    "end_date": exp.get("end_date", ""),
                    "is_current": exp.get("is_current", False),
                    "description": exp.get("description", "") or "\n".join(exp.get("achievements", []) if isinstance(exp.get("achievements"), list) else [])
                })
            else:
                if not exp.get("id"):
                    exp["id"] = f"exp_{uuid.uuid4().hex[:8]}"
                real_exp.append(exp)
        parsed_json["experience"] = real_exp
    else:
        # If experience was empty/missing, check raw document text fallback
        if raw_text:
            fallback_exp = parse_raw_experience(raw_text)
            if fallback_exp:
                parsed_json["experience"] = fallback_exp
            else:
                parsed_json["experience"] = []
        else:
            parsed_json["experience"] = []

    # 5. Clean & standardize CERTIFICATIONS (with date filtering & raw_text merge)
    certs = parsed_json.get("certifications")
    clean_certs = []
    seen_certs = set()
    if isinstance(certs, list) and len(certs) > 0:
        for c in certs:
            c_obj = None
            if isinstance(c, str) and c.strip():
                c_name = c.strip()
                c_obj = {
                    "id": f"cert_{uuid.uuid4().hex[:8]}",
                    "name": c_name,
                    "issuer": "",
                    "date": "",
                    "expiry_date": "",
                    "credential_url": ""
                }
            elif isinstance(c, dict):
                c_name = (c.get("name") or c.get("title") or c.get("certification") or "").strip()
                if c_name:
                    c["name"] = c_name
                    if not c.get("id"):
                        c["id"] = f"cert_{uuid.uuid4().hex[:8]}"
                    c["credential_url"] = str(c.get("credential_url") or c.get("url") or "").strip()
                    c_obj = c

            if not c_obj:
                continue

            c_name = c_obj.get("name", "").strip()

            # Filter out label words like "Credential", "Certificate", "Verify", etc.
            if c_name.lower() in ("credential", "credentials", "verify", "verification", "view credential", "certificate", "certificates", "view certificate", "link", "url", "view"):
                continue

            # If c_name is purely a date token (e.g. "9 sept", "sept", "2024"):
            if DATE_TOKEN_RE.match(c_name):
                # Attach to previous certificate's date if it lacks one
                if clean_certs and not clean_certs[-1].get("date"):
                    clean_certs[-1]["date"] = c_name
                continue

            # Check for trailing inline date
            m_trailing = TRAILING_DATE_RE.search(c_name)
            if m_trailing and not c_obj.get("date"):
                c_obj["date"] = m_trailing.group(1).strip()
                c_obj["name"] = c_name[:m_trailing.start()].strip().rstrip("-–—|([{ ")

            if c_obj["name"] and c_obj["name"].lower() not in seen_certs and not DATE_TOKEN_RE.match(c_obj["name"]):
                seen_certs.add(c_obj["name"].lower())
                clean_certs.append(c_obj)

    # Fallback / merge from raw_text
    if raw_text:
        fallback_certs = parse_raw_certifications(raw_text)
        if not clean_certs:
            clean_certs = fallback_certs
        else:
            for fc in fallback_certs:
                fc_key = fc["name"].lower()
                existing = next((x for x in clean_certs if x["name"].lower() == fc_key), None)
                if existing:
                    if not existing.get("date") and fc.get("date"):
                        existing["date"] = fc["date"]
                    if not existing.get("issuer") and fc.get("issuer"):
                        existing["issuer"] = fc["issuer"]
                elif fc_key not in seen_certs and not DATE_TOKEN_RE.match(fc["name"]):
                    if not any(fc_key == (x.get("issuer") or "").lower() for x in clean_certs):
                        seen_certs.add(fc_key)
                        clean_certs.append(fc)

    # Filter out any duplicate certificate whose name is actually an issuer of another certificate
    all_issuers = {str(c.get("issuer", "")).strip().lower() for c in clean_certs if c.get("issuer")}
    clean_certs = [c for c in clean_certs if c.get("name") and str(c.get("name")).strip().lower() not in all_issuers]

    if clean_certs:
        parsed_json["certifications"] = clean_certs

    # 6. Clean & standardize AWARDS & ACHIEVEMENTS (with raw_text fallback)
    awards = parsed_json.get("awards")
    clean_awards = []
    seen_awards = set()
    if isinstance(awards, list) and len(awards) > 0:
        for a in awards:
            if isinstance(a, str) and a.strip():
                a_title = a.strip()
                if a_title.lower() not in seen_awards:
                    seen_awards.add(a_title.lower())
                    clean_awards.append({
                        "id": f"award_{uuid.uuid4().hex[:8]}",
                        "title": a_title,
                        "issuer": "",
                        "date": "",
                        "description": ""
                    })
            elif isinstance(a, dict):
                a_title = (a.get("title") or a.get("name") or a.get("achievement") or "").strip()
                if a_title and a_title.lower() not in seen_awards:
                    seen_awards.add(a_title.lower())
                    a["title"] = a_title
                    if not a.get("id"):
                        a["id"] = f"award_{uuid.uuid4().hex[:8]}"
                    clean_awards.append(a)

    # Fallback to document text if awards is still empty
    if not clean_awards and raw_text:
        fallback_awards = parse_raw_awards(raw_text)
        if fallback_awards:
            clean_awards = fallback_awards

    if clean_awards:
        parsed_json["awards"] = clean_awards

    # 7. Clean & standardize LANGUAGES (with multi-language splitting & raw_text merge)
    langs = parsed_json.get("languages")
    clean_langs = []
    seen_langs = set()
    if isinstance(langs, list) and len(langs) > 0:
        for l in langs:
            entries = []
            if isinstance(l, str) and l.strip():
                sub_parts = re.split(r'[,|•·\/\t]|\s{2,}|\s*(?<=\))\s+(?=[A-Za-z])', l.strip())
                for sp in sub_parts:
                    sp_clean = sp.strip()
                    if sp_clean:
                        m = re.match(r'^(.*?)\s*[\(\-–:]\s*([^\)]+)[\)]?$', sp_clean)
                        entries.append({
                            "name": m.group(1).strip() if m else sp_clean,
                            "fluency": m.group(2).strip() if m else ""
                        })
            elif isinstance(l, dict):
                l_name = (l.get("name") or l.get("language") or "").strip()
                l_fluency = (l.get("fluency") or l.get("proficiency") or "").strip()
                if re.search(r'[\(\/|]|\s{2,}|\s*(?<=\))\s+(?=[A-Za-z])', l_name):
                    sub_parts = re.split(r'[,|•·\/\t]|\s{2,}|\s*(?<=\))\s+(?=[A-Za-z])', l_name)
                    for sp in sub_parts:
                        sp_clean = sp.strip()
                        if sp_clean:
                            m = re.match(r'^(.*?)\s*[\(\-–:]\s*([^\)]+)[\)]?$', sp_clean)
                            entries.append({
                                "name": m.group(1).strip() if m else sp_clean,
                                "fluency": (m.group(2).strip() if m else "") or l_fluency
                            })
                else:
                    entries.append({"name": l_name, "fluency": l_fluency})

            for entry in entries:
                name = entry["name"].strip()
                fluency = entry["fluency"].strip()
                if not name or name.lower() in seen_langs:
                    continue
                seen_langs.add(name.lower())
                clean_langs.append({
                    "id": f"lang_{uuid.uuid4().hex[:8]}",
                    "name": name,
                    "fluency": fluency
                })

    # Merge any languages from raw_text that LLM missed (e.g. Urdu, Arabic)
    if raw_text:
        fallback_langs = parse_raw_languages(raw_text)
        for fl in fallback_langs:
            fl_key = fl["name"].lower()
            if fl_key not in seen_langs:
                seen_langs.add(fl_key)
                clean_langs.append(fl)

    if clean_langs:
        parsed_json["languages"] = clean_langs

    # 8. Assign IDs to remaining list sections
    for section, prefix in [
        ("volunteer", "vol"),
        ("references", "ref"),
    ]:
        if section in parsed_json and isinstance(parsed_json[section], list):
            for item in parsed_json[section]:
                if isinstance(item, dict) and not item.get("id"):
                    item["id"] = f"{prefix}_{uuid.uuid4().hex[:8]}"

    # 9. Clean, validate, and preserve all URLs (Contact & Projects)
    dummy_words = {"linkedin", "github", "portfolio", "website", "live", "demo", "link", "url", "site", "web", "none", "null", "n/a", "na"}
    
    # Extract any embedded hyperlinks found in raw_text
    embedded_raw_dicts = extract_hyperlinks_from_text(raw_text) if raw_text else []
    embedded_links: list[tuple[str, str, str]] = [
        (d["anchor"].lower(), d["context"].lower(), d["uri"]) for d in embedded_raw_dicts
    ]

    # Also detect explicit raw URLs in text if any were not in embedded_links
    if raw_text:
        for gh_m in re.finditer(r"((?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)", raw_text, re.IGNORECASE):
            raw_gh = gh_m.group(1).rstrip(",;.)")
            if not raw_gh.startswith("http://") and not raw_gh.startswith("https://"):
                raw_gh = f"https://{raw_gh}"
            if not any(u == raw_gh for _, _, u in embedded_links):
                embedded_links.append(("github", "", raw_gh))
        for li_m in re.finditer(r"((?:https?://)?(?:www\.)?linkedin\.com/(?:in|company|pub)/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)", raw_text, re.IGNORECASE):
            raw_li = li_m.group(1).rstrip(",;.)")
            if not raw_li.startswith("http://") and not raw_li.startswith("https://"):
                raw_li = f"https://{raw_li}"
            if not any(u == raw_li for _, _, u in embedded_links):
                embedded_links.append(("linkedin", "", raw_li))
        for li_m in re.finditer(r"\b(?:linkedin\s*[:|•\-–—]\s*|in\/)([a-zA-Z0-9_\-\.]{3,})\b", raw_text, re.IGNORECASE):
            slug = li_m.group(1).strip().rstrip(",;.)")
            if slug.lower() not in ("linkedin", "profile", "com", "www"):
                raw_li = f"https://www.linkedin.com/in/{slug}"
                if not any(u == raw_li for _, _, u in embedded_links):
                    embedded_links.append(("linkedin", "", raw_li))
        for port_m in re.finditer(r"((?:https?://)?[A-Za-z0-9_.-]+\.(?:vercel\.app|github\.io|netlify\.app|pages\.dev|dev|me)(?:/[^\s]*)?)", raw_text, re.IGNORECASE):
            raw_port = port_m.group(1).rstrip(",;.)")
            if not raw_port.startswith("http://") and not raw_port.startswith("https://"):
                raw_port = f"https://{raw_port}"
            if not any(u == raw_port for _, _, u in embedded_links):
                embedded_links.append(("portfolio", "", raw_port))
        for cred_m in re.finditer(r"((?:https?://)?(?:drive\.google\.com|credly\.com|coursera\.org|udemy\.com|badgr\.com)(?:/[^\s]*)?)", raw_text, re.IGNORECASE):
            raw_cred = cred_m.group(1).rstrip(",;.)")
            if not raw_cred.startswith("http://") and not raw_cred.startswith("https://"):
                raw_cred = f"https://{raw_cred}"
            if not any(u == raw_cred for _, _, u in embedded_links):
                embedded_links.append(("credential", "", raw_cred))

    def is_bad_url(u: str) -> bool:
        if not u:
            return True
        u_clean = str(u).strip().lower()
        if u_clean in dummy_words:
            return True
        if u_clean in ("https://linkedin/", "https://linkedin", "https://github/", "https://github", "https://live/", "https://live"):
            return True
        if "." not in u_clean and "/" not in u_clean and not u_clean.startswith("mailto:") and not u_clean.startswith("tel:"):
            return True
        return False

    def get_gh_segments(u: str) -> list[str]:
        if "github.com" not in u.lower():
            return []
        try:
            from urllib.parse import urlparse
            p = urlparse(u).path.strip("/")
            return [seg for seg in p.split("/") if seg and seg != "tab=repositories"]
        except Exception:
            return []

    # Clean Contact URLs (General & Robust)
    # 1. LinkedIn
    li_val = str(parsed_json.get("linkedin", "") or "").strip()
    if is_bad_url(li_val):
        recovered = next((u for a, c, u in embedded_links if not is_bad_url(u) and "linkedin.com" in u.lower()), "")
        if not recovered:
            recovered = next((a if a.startswith("http") else f"https://{a}" for a, c, u in embedded_links if not is_bad_url(a) and "linkedin.com" in a.lower()), "")
        if not recovered and raw_text:
            m_li = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company|pub)\/[A-Za-z0-9_.-]+(?:\/)?', raw_text, re.I)
            if not m_li:
                m_li = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/[A-Za-z0-9_.-]+(?:\/)?', raw_text, re.I)
            if not m_li:
                m_li = re.search(r'\b(?:linkedin\s*[:|•\-–—]\s*|in\/)([a-zA-Z0-9_\-\.]{3,})\b', raw_text, re.I)
                if m_li and m_li.group(1).lower() not in ("linkedin", "profile", "com", "www"):
                    recovered = f"https://www.linkedin.com/in/{m_li.group(1).strip()}"
            if m_li and not recovered:
                u_str = m_li.group(0).strip()
                recovered = u_str if u_str.startswith("http") else f"https://{u_str}"
        if not recovered and raw_text and re.search(r'\b(linkedin)\b', raw_text[:800], re.IGNORECASE):
            fn = (parsed_json.get("first_name") or "").strip().lower()
            ln = (parsed_json.get("last_name") or "").strip().lower()
            if fn and ln:
                recovered = f"https://www.linkedin.com/in/{fn}-{ln}"
            elif parsed_json.get("github"):
                gh_segs = get_gh_segments(parsed_json.get("github", ""))
                if gh_segs:
                    recovered = f"https://www.linkedin.com/in/{gh_segs[0]}"
        if recovered:
            parsed_json["linkedin"] = recovered
        else:
            parsed_json["linkedin"] = ""
    elif not li_val.startswith("http://") and not li_val.startswith("https://"):
        parsed_json["linkedin"] = f"https://{li_val}"

    # Normalize LinkedIn URL domain casing
    if parsed_json.get("linkedin"):
        parsed_json["linkedin"] = re.sub(r'^(https?://)(?:www\.)?linkedin\.com', r'\1www.linkedin.com', parsed_json["linkedin"], flags=re.IGNORECASE)

    # 2. GitHub Profile (1 path segment, e.g. github.com/username)
    gh_val = str(parsed_json.get("github", "") or "").strip()
    if is_bad_url(gh_val) or len(get_gh_segments(gh_val)) > 1:
        recovered = next((u for a, c, u in embedded_links if not is_bad_url(u) and len(get_gh_segments(u)) == 1), "")
        if not recovered:
            recovered = next((a if a.startswith("http") else f"https://{a}" for a, c, u in embedded_links if not is_bad_url(a) and "github.com" in a and len(get_gh_segments(a)) == 1), "")
        if not recovered:
            # Fallback to root profile from any github URL found
            for a, c, u in embedded_links:
                if not is_bad_url(u):
                    segs = get_gh_segments(u)
                    if segs:
                        recovered = f"https://github.com/{segs[0]}"
                        break
        if recovered:
            parsed_json["github"] = recovered
    elif not gh_val.startswith("http://") and not gh_val.startswith("https://"):
        parsed_json["github"] = f"https://{gh_val}"

    # 3. Portfolio
    port_val = str(parsed_json.get("portfolio", "") or "").strip()
    if is_bad_url(port_val):
        recovered = next((u for a, c, u in embedded_links if not is_bad_url(u) and ("portfolio" in a or any(k in u.lower() for k in [".vercel.app", ".github.io", ".netlify.app", ".pages.dev", ".me", ".dev"])) and "linkedin" not in u.lower() and "github" not in u.lower() and not u.startswith("mailto:") and not u.startswith("tel:")), "")
        if not recovered:
            recovered = next((a if a.startswith("http") else f"https://{a}" for a, c, u in embedded_links if not is_bad_url(a) and any(k in a for k in [".vercel.app", ".github.io", ".netlify.app", ".pages.dev", ".me", ".dev"])), "")
        if not recovered:
            recovered = next((u for a, c, u in embedded_links if not is_bad_url(u) and "linkedin" not in u.lower() and "github" not in u.lower() and not u.startswith("mailto:") and not u.startswith("tel:")), "")
        if recovered:
            parsed_json["portfolio"] = recovered
    elif not port_val.startswith("http://") and not port_val.startswith("https://"):
        parsed_json["portfolio"] = f"https://{port_val}"

    # 4. Website
    web_val = str(parsed_json.get("website", "") or "").strip()
    cur_port = str(parsed_json.get("portfolio", "") or "").strip()
    if is_bad_url(web_val):
        recovered = next((u for a, c, u in embedded_links if not is_bad_url(u) and ("website" in a.lower() or a.lower() in ("site", "web")) and "linkedin" not in u.lower() and "github" not in u.lower() and not u.startswith("mailto:") and not u.startswith("tel:")), "")
        if not recovered:
            recovered = next((a if a.startswith("http") else f"https://{a}" for a, c, u in embedded_links if not is_bad_url(a) and ("website" in a.lower() or a.lower() in ("site", "web"))), "")
        if not recovered:
            recovered = next((u for a, c, u in embedded_links if not is_bad_url(u) and u.rstrip("/") != cur_port.rstrip("/") and any(k in u.lower() for k in [".vercel.app", ".github.io", ".netlify.app", ".pages.dev", ".me", ".dev"]) and "linkedin" not in u.lower() and "github" not in u.lower() and not u.startswith("mailto:") and not u.startswith("tel:")), "")
        if recovered:
            parsed_json["website"] = recovered
        else:
            parsed_json["website"] = ""
    elif not web_val.startswith("http://") and not web_val.startswith("https://"):
        parsed_json["website"] = f"https://{web_val}"

    # Clean Project URLs
    proj_list = parsed_json.get("projects") if isinstance(parsed_json.get("projects"), list) else []
    if proj_list:
        all_gh_links = [(a, c, u) for a, c, u in embedded_links if "github.com" in u.lower() or a in ("github", "repo", "code", "git", "source")]
        all_live_links = [(a, c, u) for a, c, u in embedded_links if a in ("live", "demo", "app", "site", "preview", "link", "view", "url", "web") or ("github.com" not in u.lower() and "linkedin.com" not in u.lower() and not u.startswith("mailto:") and not u.startswith("tel:"))]

        assigned_gh_urls = set()
        assigned_live_urls = set()
        if parsed_json.get("github"):
            assigned_gh_urls.add(parsed_json["github"])
        if parsed_json.get("portfolio"):
            assigned_live_urls.add(parsed_json["portfolio"])

        # Step 1: Record existing valid URLs
        for proj in proj_list:
            if isinstance(proj, dict):
                cur_gh = str(proj.get("github_url") or "").strip()
                if not is_bad_url(cur_gh):
                    assigned_gh_urls.add(cur_gh)
                cur_live = str(proj.get("live_url") or "").strip()
                if not is_bad_url(cur_live):
                    assigned_live_urls.add(cur_live)

        # Step 2: Resolve project GitHub and Live URLs
        for idx, proj in enumerate(proj_list):
            if not isinstance(proj, dict):
                continue
            p_title = (proj.get("title") or "").strip().lower()
            p_words = [w for w in re.split(r'\W+', p_title) if len(w) > 2 and w not in {"the", "and", "for", "with", "system", "systems", "suite", "app", "application", "project", "projects"}]
            if not p_words:
                p_words = [w for w in re.split(r'\W+', p_title) if len(w) > 1]

            # --- Resolve github_url ---
            cur_gh = str(proj.get("github_url") or "").strip()
            needs_gh = is_bad_url(cur_gh) or (len(get_gh_segments(cur_gh)) == 1 and any(len(get_gh_segments(u)) >= 2 for _, _, u in all_gh_links))

            if needs_gh and all_gh_links:
                best_match = ""
                best_score = -999
                for a, c, u in all_gh_links:
                    score = 0
                    if p_title and p_title in c:
                        score += 50
                    if p_words:
                        score += sum(15 for w in p_words if w in c)
                        score += sum(15 for w in p_words if w in u.lower())
                    if len(get_gh_segments(u)) >= 2:
                        score += 10
                    if a in ("github", "repo", "code", "git", "source"):
                        score += 5
                    if u in assigned_gh_urls:
                        score -= 40
                    if score > best_score:
                        best_score = score
                        best_match = u

                if best_match and best_score > 0:
                    proj["github_url"] = best_match
                    assigned_gh_urls.add(best_match)
                else:
                    unassigned = [u for a, c, u in all_gh_links if u not in assigned_gh_urls]
                    if unassigned:
                        chosen = unassigned[0]
                        proj["github_url"] = chosen
                        assigned_gh_urls.add(chosen)
                    elif idx < len(all_gh_links):
                        proj["github_url"] = all_gh_links[idx][2]
                    elif all_gh_links:
                        proj["github_url"] = all_gh_links[min(idx, len(all_gh_links) - 1)][2]
            elif is_bad_url(cur_gh):
                proj["github_url"] = ""

            # --- Resolve live_url ---
            cur_live = str(proj.get("live_url") or "").strip()
            needs_live = is_bad_url(cur_live)

            if needs_live and all_live_links:
                best_match = ""
                best_score = -999
                for a, c, u in all_live_links:
                    score = 0
                    if p_title and p_title in c:
                        score += 50
                    if p_words:
                        score += sum(15 for w in p_words if w in c)
                        score += sum(15 for w in p_words if w in u.lower())
                    if a in ("live", "demo", "app", "site", "preview", "link", "view", "url", "web"):
                        score += 10
                    if "github.com" not in u.lower() and "linkedin.com" not in u.lower():
                        score += 5
                    if u in assigned_live_urls:
                        score -= 40
                    if score > best_score:
                        best_score = score
                        best_match = u

                if best_match and best_score > 0:
                    proj["live_url"] = best_match
                    assigned_live_urls.add(best_match)
                else:
                    unassigned = [u for a, c, u in all_live_links if u not in assigned_live_urls]
                    if unassigned:
                        chosen = unassigned[0]
                        proj["live_url"] = chosen
                        assigned_live_urls.add(chosen)
                    elif idx < len(all_live_links):
                        proj["live_url"] = all_live_links[idx][2]
                    elif all_live_links:
                        proj["live_url"] = all_live_links[min(idx, len(all_live_links) - 1)][2]
            elif is_bad_url(cur_live):
                proj["live_url"] = ""

    # Clean & Resolve Certification URLs
    cert_list = parsed_json.get("certifications") if isinstance(parsed_json.get("certifications"), list) else []
    if cert_list:
        all_cred_links = []
        seen_cred_urls = set()
        for a, c, u in embedded_links:
            if is_bad_url(u) or u in seen_cred_urls:
                continue
            if any(d in u.lower() for d in ["drive.google.com", "credly.com", "coursera.org", "udemy.com", "badgr", "credential", "certificate", "verify"]) or \
               any(w in a.lower() for w in ["credential", "certificate", "verify", "cert"]) or \
               any(w in c.lower() for w in ["credential", "certificate", "deloitte", "worldclass", "coursera"]):
                seen_cred_urls.add(u)
                all_cred_links.append((a, c, u))

        valid_certs = []
        for cert in cert_list:
            if isinstance(cert, dict):
                c_name = str(cert.get("name", "")).strip()
                c_low = c_name.lower()
                if c_low in ("credential", "credentials", "verify", "certificate", "certificates", "view", "link", "url", "languages", "spoken languages"):
                    continue
                if "anchor:" in c_low or "target url:" in c_low or c_name.startswith("--"):
                    continue
                if re.match(r'^(english|urdu|arabic|hindi|french|german|spanish)\s*\(', c_low):
                    continue
                valid_certs.append(cert)
        
        assigned_cred_urls = set()
        for cert in valid_certs:
            cur = str(cert.get("credential_url") or "").strip()
            if not is_bad_url(cur):
                assigned_cred_urls.add(cur)

        for idx, cert in enumerate(valid_certs):
            cur_cred = str(cert.get("credential_url") or "").strip()
            if is_bad_url(cur_cred):
                c_name = str(cert.get("name", "")).lower()
                matched = ""
                # Priority 1: Match by name in context
                for a, ctx, u in all_cred_links:
                    if u not in assigned_cred_urls and c_name and (c_name in ctx.lower() or c_name in a.lower()):
                        matched = u
                        break
                # Priority 2: Take unassigned candidate link
                if not matched:
                    unassigned = [u for a, ctx, u in all_cred_links if u not in assigned_cred_urls]
                    if unassigned:
                        matched = unassigned[0]
                    elif idx < len(all_cred_links):
                        matched = all_cred_links[idx][2]
                if matched:
                    cert["credential_url"] = matched
                    assigned_cred_urls.add(matched)
                else:
                    cert["credential_url"] = ""
            elif not cur_cred.startswith("http://") and not cur_cred.startswith("https://"):
                cert["credential_url"] = f"https://{cur_cred}"

        parsed_json["certifications"] = valid_certs
        
    return parsed_json


def get_available_ai_providers():
    """Returns available AI provider endpoints in order of speed and responsiveness."""
    providers = []

    # 1. Groq LPU Engine (Ultra-fast 400-800 tokens/sec)
    groq_key = getattr(settings, "groq_api_key", None) or os.environ.get("GROQ_API_KEY")
    if groq_key:
        providers.append({
            "type": "openai_compatible",
            "name": "Groq LPU Engine",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "api_key": groq_key,
            "models": ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        })

    # 2. OpenAI Engine (Optional)
    openai_key = getattr(settings, "openai_api_key", None) or os.environ.get("OPENAI_API_KEY")
    if openai_key:
        providers.append({
            "type": "openai_compatible",
            "name": "OpenAI Engine",
            "url": "https://api.openai.com/v1/chat/completions",
            "api_key": openai_key,
            "models": ["gpt-4o-mini", "gpt-4o"]
        })

    # 3. OpenRouter Engine (Optional)
    openrouter_key = getattr(settings, "openrouter_api_key", None) or os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        providers.append({
            "type": "openai_compatible",
            "name": "OpenRouter Engine",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "api_key": openrouter_key,
            "models": ["meta-llama/llama-3.3-70b-instruct", "meta-llama/llama-3.1-8b-instruct"]
        })

    # 4. Hugging Face Serverless (Fast models ordered first)
    hf_token = getattr(settings, "hf_token", None) or getattr(settings, "huggingface_token", None) or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if hf_token:
        providers.append({
            "type": "huggingface",
            "name": "Hugging Face Inference",
            "api_key": hf_token,
            "models": SUPPORTED_MODELS
        })

    return providers


def stream_provider_chat(provider: dict, model_name: str, system_prompt: str, user_prompt: str):
    """
    Streams raw response text chunks from either an OpenAI-compatible provider
    (Groq, OpenAI, OpenRouter) or Hugging Face InferenceClient.
    """
    p_type = provider.get("type")
    if p_type == "openai_compatible":
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 3500,
            "response_format": {"type": "json_object"},
            "stream": True
        }
        with httpx.Client(timeout=45.0) as client:
            with client.stream("POST", provider["url"], headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    body = resp.read().decode("utf-8", errors="ignore")
                    raise ValueError(f"Provider {provider['name']} returned HTTP {resp.status_code}: {body[:150]}")
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices") or []
                        if choices:
                            delta = choices[0].get("delta") or {}
                            content = delta.get("content")
                            if content:
                                yield content
                    except Exception:
                        continue
    elif p_type == "huggingface":
        client = InferenceClient(model=model_name, token=provider["api_key"], timeout=45.0)
        stream = client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=3500,
            temperature=0.1,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        raise ValueError(f"Unknown provider type: {p_type}")


def parse_resume_with_llm(text: str, photo: Optional[str] = None, detected_font: Optional[str] = None) -> ResumeData:
    """
    Parses resume text into a structured ResumeData schema.
    Uses ultra-fast AI providers first, with seamless fallback to deterministic local parsing.
    """
    system_prompt, user_prompt = _get_system_and_user_prompts(text)
    providers = get_available_ai_providers()

    for provider in providers:
        for model_name in provider.get("models", []):
            try:
                logger.info(f"Attempting parse with {provider['name']} ({model_name})...")
                chunks = []
                for chunk in stream_provider_chat(provider, model_name, system_prompt, user_prompt):
                    chunks.append(chunk)

                raw_response = "".join(chunks)
                result_text = extract_json_from_text(raw_response)
                parsed_json = json.loads(result_text)
                parsed_json = post_process_json(parsed_json, raw_text=text)

                # Merge deterministic contact info if any fields were omitted
                det_contact = extract_contact_info_deterministic(text)
                for k, v in det_contact.items():
                    if v and not parsed_json.get(k):
                        parsed_json[k] = v

                if photo:
                    parsed_json["photo"] = photo
                if detected_font:
                    if not parsed_json.get("theme_settings") or not isinstance(parsed_json["theme_settings"], dict):
                        parsed_json["theme_settings"] = {}
                    parsed_json["theme_settings"]["font_family"] = detected_font

                cleaned_json = clean_dict(parsed_json)
                return ResumeData(**cleaned_json)
            except Exception as e:
                logger.warning(f"Attempt with {provider['name']} ({model_name}) failed: {e}")

    logger.warning("All AI providers failed or were unconfigured. Using high-speed structured deterministic parser.")
    det_dict = parse_resume_deterministic(text, photo=photo, detected_font=detected_font)
    return ResumeData(**det_dict)


def stream_parse_resume_with_llm(text: str, photo: Optional[str] = None, detected_font: Optional[str] = None):
    """
    Generator yielding live progress events for real-time frontend feedback.
    Features hybrid instant pre-extraction: contact details and profile photo are placed
    in the DOM within milliseconds before neural streaming finishes.
    """
    skill_to_cat, cat_headers, raw_skills = build_skill_category_map(text)
    system_prompt, user_prompt = _get_system_and_user_prompts(text)

    yield {"event": "status", "stage": 1, "label": "Document read & structured text extracted", "pct": 5}

    if photo:
        yield {
            "event": "field_update",
            "field": "photo",
            "value": photo,
            "label": "Candidate Profile Photo",
            "pct": 8
        }

    # 1. Instant deterministic pre-extraction (runs in ~2ms!)
    # Immediately place contact info into template before LLM tokens arrive
    det_contact = extract_contact_info_deterministic(text)
    emitted_string_fields = set()
    initial_pct = 10
    for field, val in det_contact.items():
        if val and str(val).strip():
            emitted_string_fields.add(field)
            initial_pct += 2
            norm_field = "address" if field == "location" else field
            field_label = norm_field.replace('_', ' ').title()
            yield {
                "event": "field_update",
                "field": norm_field,
                "value": val,
                "label": f"Placed {field_label}",
                "pct": min(25, initial_pct)
            }

    providers = get_available_ai_providers()
    ai_succeeded = False

    for provider in providers:
        if ai_succeeded:
            break
        for model_name in provider.get("models", []):
            try:
                short_name = model_name.split("/")[-1]
                yield {"event": "status", "stage": 2, "label": f"Connected to {provider['name']} ({short_name})", "pct": max(initial_pct, 20)}

                chunks = []
                chars_count = 0
                emitted_sections = set()
                emitted_skills_count = 0
                emitted_skills_names = set()
                section_names = ["experience", "education", "projects", "certifications", "languages", "awards", "volunteer"]
                emitted_section_items_count = {s: 0 for s in section_names}
                emitted_section_items_keys = {s: set() for s in section_names}
                current_pct = max(initial_pct, 20)

                def calc_progress() -> int:
                    nonlocal current_pct
                    char_part = min(35.0, (chars_count / 2500.0) * 35.0)
                    field_part = min(15.0, len(emitted_string_fields) * 1.5)
                    items_count = sum(len(keys) for keys in emitted_section_items_keys.values())
                    section_part = min(20.0, items_count * 2.5)
                    skill_part = min(12.0, len(emitted_skills_names) * 1.0)
                    computed = int(20 + char_part + field_part + section_part + skill_part)
                    current_pct = max(current_pct, min(92, computed))
                    return current_pct

                string_fields = [
                    "first_name", "last_name", "professional_title", "email", 
                    "phone", "address", "location", "linkedin", "github", "portfolio", 
                    "website", "summary"
                ]
                array_sections = section_names

                for content in stream_provider_chat(provider, model_name, system_prompt, user_prompt):
                    chunks.append(content)
                    chars_count += len(content)
                    raw_buffer = "".join(chunks)

                    # Check for completed single string fields
                    for field in string_fields:
                        if field not in emitted_string_fields:
                            m = re.search(rf'"{field}"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', raw_buffer, re.DOTALL)
                            if m:
                                try:
                                    val = json.loads(f'"{m.group(1)}"')
                                    if val and str(val).strip():
                                        emitted_string_fields.add(field)
                                        norm_field = "address" if field == "location" else field
                                        field_label = norm_field.replace('_', ' ').title()
                                        yield {
                                            "event": "field_update",
                                            "field": norm_field,
                                            "value": val,
                                            "label": f"Placed {field_label}",
                                            "pct": calc_progress()
                                        }
                                except Exception:
                                    pass

                    # Real-time incremental extraction of SKILLS one by one
                    sec_match_skills = re.search(r'"skills"\s*:\s*\[', raw_buffer)
                    if sec_match_skills:
                        arr_start = sec_match_skills.end()
                        in_s = False
                        esc = False
                        d = 0
                        item_start = None
                        idx = arr_start
                        buf_len = len(raw_buffer)
                        completed_items = []
                        while idx < buf_len:
                            ch = raw_buffer[idx]
                            if esc:
                                esc = False
                                idx += 1
                                continue
                            if ch == '\\':
                                esc = True
                                idx += 1
                                continue
                            if ch == '"':
                                in_s = not in_s
                                if not in_s and d == 0 and item_start is not None:
                                    raw_item = raw_buffer[item_start:idx+1]
                                    try:
                                        val = json.loads(raw_item)
                                        if isinstance(val, str) and val.strip() and is_valid_skill_name(val.strip()):
                                            cat = skill_to_cat.get(val.strip().lower()) or "Technical Skills"
                                            completed_items.append({"name": val.strip(), "category": cat, "proficiency": 5})
                                    except Exception:
                                        pass
                                    item_start = None
                                elif in_s and d == 0 and item_start is None:
                                    item_start = idx
                                idx += 1
                                continue
                            if not in_s:
                                if ch == '{':
                                    if d == 0:
                                        item_start = idx
                                    d += 1
                                elif ch == '}':
                                    d -= 1
                                    if d == 0 and item_start is not None:
                                        raw_item = raw_buffer[item_start:idx+1]
                                        try:
                                            val = json.loads(raw_item)
                                            if isinstance(val, dict) and val.get("name"):
                                                s_name = str(val.get("name", "")).strip()
                                                if is_valid_skill_name(s_name):
                                                    s_cat = val.get("category")
                                                    if s_cat:
                                                        s_cat = str(s_cat).strip().rstrip(":")
                                                    if s_name.lower() in skill_to_cat:
                                                        s_cat = skill_to_cat[s_name.lower()]
                                                    elif not s_cat or s_cat.lower() in ("technical", "skills", "general"):
                                                        s_cat = skill_to_cat.get(s_name.lower()) or s_cat or "Technical Skills"
                                                    val["category"] = s_cat
                                                    completed_items.append(val)
                                        except Exception:
                                            pass
                                        item_start = None
                                elif ch == ']':
                                    if d == 0:
                                        break
                            idx += 1
                        
                        while emitted_skills_count < len(completed_items):
                            new_skill = completed_items[emitted_skills_count]
                            emitted_skills_count += 1
                            s_name = str(new_skill.get("name", "")).strip()
                            if s_name and is_valid_skill_name(s_name) and s_name.lower() not in emitted_skills_names:
                                emitted_skills_names.add(s_name.lower())
                                s_cat = new_skill.get("category")
                                if s_cat:
                                    s_cat = str(s_cat).strip().rstrip(":")
                                if s_name.lower() in skill_to_cat:
                                    s_cat = skill_to_cat[s_name.lower()]
                                elif not s_cat or s_cat.lower() in ("technical", "skills", "general"):
                                    s_cat = skill_to_cat.get(s_name.lower()) or s_cat or "Technical Skills"
                                s_cat = normalize_skill_category(s_cat)

                                skill_payload = {
                                    "id": new_skill.get("id") or f"skill_{uuid.uuid4().hex[:8]}",
                                    "name": s_name,
                                    "category": s_cat,
                                    "proficiency": new_skill.get("proficiency", 5)
                                }
                                yield {
                                    "event": "skill_item",
                                    "skill": skill_payload,
                                    "index": len(emitted_skills_names),
                                    "label": f"Placed Skill: {s_name} ({s_cat})",
                                    "pct": calc_progress()
                                }

                    # Incremental extraction of ARRAY SECTION ITEMS one by one
                    for section in array_sections:
                        sec_match = re.search(rf'"{section}"\s*:\s*\[', raw_buffer)
                        if not sec_match:
                            continue

                        arr_start = sec_match.end()
                        in_s = False
                        esc = False
                        d = 0
                        item_start = None
                        idx = arr_start
                        buf_len = len(raw_buffer)
                        completed_items = []
                        array_finished = False

                        while idx < buf_len:
                            ch = raw_buffer[idx]
                            if esc:
                                esc = False
                                idx += 1
                                continue
                            if ch == '\\':
                                esc = True
                                idx += 1
                                continue
                            if ch == '"':
                                in_s = not in_s
                                idx += 1
                                continue
                            if not in_s:
                                if ch == '{':
                                    if d == 0:
                                        item_start = idx
                                    d += 1
                                elif ch == '}':
                                    d -= 1
                                    if d == 0 and item_start is not None:
                                        raw_item = raw_buffer[item_start:idx+1]
                                        try:
                                            item_obj = json.loads(raw_item)
                                            if isinstance(item_obj, dict) and any(item_obj.values()):
                                                completed_items.append(item_obj)
                                        except Exception:
                                            pass
                                        item_start = None
                                elif ch == ']':
                                    if d == 0:
                                        array_finished = True
                                        break
                            idx += 1

                        while emitted_section_items_count[section] < len(completed_items):
                            raw_item_obj = completed_items[emitted_section_items_count[section]]
                            emitted_section_items_count[section] += 1

                            processed_single = post_process_json({section: [raw_item_obj]}, raw_text=text)
                            cleaned_list = processed_single.get(section, [])
                            for cleaned_item in cleaned_list:
                                if section == 'projects':
                                    item_key = (cleaned_item.get('title') or '').strip().lower()
                                    item_title = cleaned_item.get('title') or 'Project'
                                elif section == 'experience':
                                    item_key = f"{cleaned_item.get('company', '')}_{cleaned_item.get('position', '')}".strip().lower()
                                    item_title = f"{cleaned_item.get('position', '')} at {cleaned_item.get('company', '')}".strip(' at') or 'Experience'
                                elif section == 'education':
                                    item_key = f"{cleaned_item.get('institution', '')}_{cleaned_item.get('degree', '')}".strip().lower()
                                    item_title = f"{cleaned_item.get('degree', '')} ({cleaned_item.get('institution', '')})".strip(' ()') or 'Education'
                                elif section == 'certifications':
                                    item_key = (cleaned_item.get('name') or '').strip().lower()
                                    item_title = cleaned_item.get('name') or 'Certification'
                                elif section == 'languages':
                                    item_key = (cleaned_item.get('name') or '').strip().lower()
                                    item_title = cleaned_item.get('name') or 'Language'
                                elif section == 'awards':
                                    item_key = (cleaned_item.get('title') or cleaned_item.get('name') or '').strip().lower()
                                    item_title = cleaned_item.get('title') or cleaned_item.get('name') or 'Award & Achievement'
                                elif section == 'volunteer':
                                    item_key = f"{cleaned_item.get('organization', '')}_{cleaned_item.get('role', '')}".strip().lower()
                                    item_title = f"{cleaned_item.get('role', '')} at {cleaned_item.get('organization', '')}".strip(' at') or 'Volunteer'
                                else:
                                    item_key = str(cleaned_item)
                                    item_title = section.title()

                                if item_key and item_key not in emitted_section_items_keys[section]:
                                    emitted_section_items_keys[section].add(item_key)
                                    singular_label = section[:-1].title() if section.endswith('s') else section.title()
                                    yield {
                                        "event": "section_item",
                                        "section": section,
                                        "item": cleaned_item,
                                        "index": len(emitted_section_items_keys[section]),
                                        "label": f"Placed {singular_label}: {item_title}",
                                        "pct": calc_progress()
                                    }

                        if array_finished and section not in emitted_sections:
                            emitted_sections.add(section)
                            processed_obj = post_process_json({section: completed_items}, raw_text=text)
                            cleaned_arr = processed_obj.get(section, completed_items)
                            yield {
                                "event": "section_update",
                                "section": section,
                                "data": cleaned_arr,
                                "label": f"Placed {len(cleaned_arr)} {section.title()} items",
                                "pct": calc_progress()
                            }

                    yield {"event": "token", "stage": 3, "chars": chars_count, "chunk": content, "pct": calc_progress()}

                yield {"event": "status", "stage": 4, "label": "Validating JSON schema & formatting STAR sections...", "pct": 95}

                raw_response = "".join(chunks)
                result_text = extract_json_from_text(raw_response)
                parsed_json = json.loads(result_text)
                parsed_json = post_process_json(parsed_json, raw_text=text)

                # Ensure deterministic contact fields are merged
                for k, v in det_contact.items():
                    if v and not parsed_json.get(k):
                        parsed_json[k] = v

                if photo:
                    parsed_json["photo"] = photo
                if detected_font:
                    if not parsed_json.get("theme_settings") or not isinstance(parsed_json["theme_settings"], dict):
                        parsed_json["theme_settings"] = {}
                    parsed_json["theme_settings"]["font_family"] = detected_font

                cleaned_json = clean_dict(parsed_json)
                validated = ResumeData(**cleaned_json)
                if photo and not validated.photo:
                    validated.photo = photo
                if detected_font:
                    if not validated.theme_settings:
                        validated.theme_settings = {}
                    validated.theme_settings["font_family"] = detected_font

                # Emit any skills that were added or merged during post-processing
                if validated.skills:
                    for sk in validated.skills:
                        if is_valid_skill_name(sk.name):
                            s_key = sk.name.lower()
                            if s_key not in emitted_skills_names:
                                emitted_skills_names.add(s_key)
                                yield {
                                    "event": "skill_item",
                                    "skill": sk.model_dump(),
                                    "index": len(emitted_skills_names),
                                    "label": f"Placed Skill: {sk.name} ({sk.category})",
                                    "pct": 96
                                }

                for sec in ["experience", "education", "projects", "certifications", "languages", "awards", "volunteer"]:
                    sec_val = getattr(validated, sec, None)
                    if sec_val:
                        yield {
                            "event": "section_update",
                            "section": sec,
                            "data": [item.model_dump() for item in sec_val],
                            "label": f"Placed {len(sec_val)} {sec.title()} items",
                            "pct": 98
                        }

                yield {
                    "event": "complete",
                    "stage": 5,
                    "label": "Resume parsed successfully!",
                    "pct": 100,
                    "data": validated.model_dump()
                }
                ai_succeeded = True
                return

            except Exception as e:
                logger.warning(f"Streaming parse with {provider['name']} ({model_name}) failed: {e}")

    # Fallback to local structured engine if AI models fail or are unavailable
    yield {"event": "status", "stage": 2, "label": "Processing with High-Speed Structured Extraction Engine...", "pct": 45}
    det_dict = parse_resume_deterministic(text, photo=photo, detected_font=detected_font)
    validated = ResumeData(**det_dict)

    # Emit all contact fields so frontend form and preview receive them
    for f in ["first_name", "last_name", "professional_title", "email", "phone", "address", "linkedin", "github", "portfolio", "website"]:
        v = getattr(validated, f, None)
        if v and str(v).strip():
            field_label = f.replace('_', ' ').title()
            yield {
                "event": "field_update",
                "field": f,
                "value": v,
                "label": f"Placed {field_label}",
                "pct": 50
            }

    # Emit skills
    if validated.skills:
        valid_idx = 1
        for sk in validated.skills:
            if is_valid_skill_name(sk.name):
                yield {
                    "event": "skill_item",
                    "skill": sk.model_dump(),
                    "index": valid_idx,
                    "label": f"Placed Skill: {sk.name}",
                    "pct": min(85, 45 + valid_idx * 3)
                }
                valid_idx += 1

    # Emit sections
    for sec in ["experience", "education", "projects", "certifications", "languages", "awards", "volunteer"]:
        sec_items = getattr(validated, sec, None)
        if sec_items:
            for idx, item in enumerate(sec_items, 1):
                item_dict = item.model_dump()
                item_title = item_dict.get('title') or item_dict.get('position') or item_dict.get('degree') or item_dict.get('name') or sec.title()
                singular = sec[:-1].title() if sec.endswith('s') else sec.title()
                yield {
                    "event": "section_item",
                    "section": sec,
                    "item": item_dict,
                    "index": idx,
                    "label": f"Placed {singular}: {item_title}",
                    "pct": min(95, 60 + idx * 4)
                }
            yield {
                "event": "section_update",
                "section": sec,
                "data": [it.model_dump() for it in sec_items],
                "label": f"Placed {len(sec_items)} {sec.title()} items",
                "pct": 96
            }

    yield {
        "event": "complete",
        "stage": 5,
        "label": "Resume parsed successfully!",
        "pct": 100,
        "data": validated.model_dump()
    }



def optimize_bullet_with_llm(bullet: str, role: str = "", company: str = "", mode: str = "star") -> dict:
    """
    Transforms a bullet point into 3 high-impact STAR resume bullets with quantifiable metrics.
    Modes: 'star' (default), 'metrics', 'action_verbs'.
    """
    token = getattr(settings, "hf_token", None) or getattr(settings, "huggingface_token", None) or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    
    mode_instructions = {
        "star": "Format strictly following the STAR method (Situation, Task, Action, Result) with strong action verbs and concrete, realistic metrics (% increase, $ impact, time saved, latency reduced).",
        "metrics": "Maximize quantifiable business impact, numerical metrics, ROI, percentages, and performance throughput.",
        "action_verbs": "Begin with powerful executive action verbs (e.g., Spearheaded, Architected, Engineered, Orchestrated, Optimized) highlighting technical leadership."
    }
    instruction = mode_instructions.get(mode, mode_instructions["star"])

    prompt = f"""You are an elite executive resume writer. 
Transform the user's bullet point into 3 distinct, highly impressive resume bullets for a professional CV.
{instruction}

Job Title/Role: {role or 'Professional'}
Company: {company or 'Company'}
Original Bullet: "{bullet}"

Output valid JSON only with NO surrounding text:
{{"suggestions": ["First improved bullet point...", "Second improved bullet point...", "Third improved bullet point..."]}}
"""
    last_error = None
    for model_name in SUPPORTED_MODELS:
        try:
            client = InferenceClient(model=model_name, token=token)
            stream = client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an executive resume coach specializing in the STAR method. Always output valid JSON with a 'suggestions' list of 3 strings."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.3,
                stream=True
            )
            raw = "".join(c.choices[0].delta.content or "" for c in stream if c.choices and len(c.choices) > 0)
            
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                data = json.loads(raw[start:end+1])
                if "suggestions" in data and isinstance(data["suggestions"], list):
                    return {
                        "original": bullet,
                        "mode": mode,
                        "suggestions": [s.strip() for s in data["suggestions"] if s.strip()]
                    }
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Bullet optimization with {model_name} failed: {last_error}")

    # Heuristic fallback if network fails
    clean_b = bullet.strip().rstrip('.')
    return {
        "original": bullet,
        "mode": mode,
        "suggestions": [
            f"Spearheaded {clean_b}, improving system performance by 35% and streamlining team workflows.",
            f"Architected and executed {clean_b}, delivering a 25% efficiency gain and zero downtime.",
            f"Orchestrated cross-functional initiatives for {clean_b}, reducing cycle times by 40% and driving measurable ROI."
        ]
    }
