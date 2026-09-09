import json
import logging
import re
import uuid
from typing import Optional
import fitz  # PyMuPDF
from huggingface_hub import InferenceClient

from app.core.config import settings
from app.schemas.resume import ResumeData

logger = logging.getLogger(__name__)

# Primary high-reasoning models verified on HF serverless router
SUPPORTED_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "Qwen/Qwen2.5-Coder-32B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct"
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from a digital PDF using PyMuPDF.
    Sorts blocks by physical layout (Y, then X) to preserve document structure.
    """
    try:
        doc = fitz.open("pdf", file_bytes)
        text = ""
        for page in doc:
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (round(b[1] / 10), b[0]))
            for b in blocks:
                if b[6] == 0:  # text block
                    text += b[4].strip() + "\n\n"
        
        text = text.strip()
        if not text:
            raise ValueError("No extractable text found in the PDF. Scanned images are not currently supported.")
            
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        raise ValueError(f"Could not read PDF file: {str(e)}")


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
    if len(words) > 1500:
        text = " ".join(words[:1500])

    minimal_schema = {
        "photo": None, "first_name": "", "last_name": "", "professional_title": "", "email": "", "phone": "",
        "address": "", "linkedin": "", "github": "", "portfolio": "", "website": "", "nationality": "", "summary": "",
        "education": [{"degree": "", "field_of_study": "", "institution": "", "location": "", "start_date": "", "end_date": "", "is_current": False, "grade": ""}],
        "experience": [{"company": "", "position": "", "location": "", "start_date": "", "end_date": "", "is_current": False, "achievements": [""]}],
        "projects": [{"title": "", "date": "", "description": "", "technologies": [""], "github_url": "", "live_url": "", "highlights": [""]}],
        "skills": [{"name": "", "category": "Technical Skills", "proficiency": 5}],
        "languages": [{"name": "", "fluency": ""}],
        "certifications": [{"name": "", "issuer": "", "date": "", "expiry_date": ""}],
        "awards": [{"title": "", "issuer": "", "date": "", "description": ""}],
        "volunteer": [{"organization": "", "role": "", "location": "", "start_date": "", "end_date": "", "is_current": False, "description": ""}]
    }
    
    system_prompt = f"""You are an elite, highly intelligent Resume Parsing AI. 
Your job is to extract information from the user's raw resume text and output ONLY a valid JSON object.
The JSON object MUST strictly adhere to the following JSON structure (omit empty fields):
{json.dumps(minimal_schema, indent=2)}

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
   - "Tools" (Git, GitHub, Docker, VS Code, Linux, Postman, Figma, Cloud platforms, etc.)
   - "Soft Skills" (Communication, Leadership, Problem Solving, Teamwork, etc.)
   Or use the explicit category header from the resume text.
   For EVERY skill:
   - 'name': specific skill name (e.g. "Python", "Next.js", "Docker", "Git").
   - 'category': its category ("Technical Skills", "Frameworks & Libraries", "Tools", or "Soft Skills").
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
7. LINKS & URLS:
   Preserve all links (LinkedIn, GitHub, Portfolio, Website, project repositories and demos). If a URL is written without http/https (e.g. "github.com/username", "LinkedIn.com/in/..."), preserve it accurately.
8. EDUCATION GRADE:
   Extract GPA, grades, or academic standing (e.g. "2.85/4.0", "3.8 GPA") into the 'grade' field of education.
9. CERTIFICATIONS & CERTIFICATES:
   Extract ALL certifications, certificates, licenses, credentials, and courses from sections titled "Certifications", "Certificates", "Licenses & Certifications", "Courses", etc. into the "certifications" array.
   - 'name': Exact certification name or title (e.g. "AWS Certified Solutions Architect", "Meta Front-End Developer", or whatever title is listed).
   - 'issuer': Issuing organization or platform (e.g. "Amazon Web Services", "Coursera", "Google", or empty string).
   - 'date': Date or year (or empty string).
   - 'expiry_date': Expiration date (or empty string).
   CRITICAL: If a resume has a "CERTIFICATIONS" or "CERTIFICATES" section, even with brief, single-word or short entries, ALWAYS extract every entry into 'certifications' with 'name'. NEVER ignore or drop them!
10. AWARDS & ACHIEVEMENTS:
   Extract ALL awards, achievements, honors, competition wins, hackathons, and recognitions from sections titled "Achievements", "Key Achievements", "Awards", "Honors & Awards", "Accomplishments", "Awards & Achievements", etc. into the "awards" array.
   - 'title': Achievement or award title.
   - 'issuer': Issuing body, competition, university, or company, or empty string.
   - 'date': Date or year, or empty string.
   - 'description': Full achievement details or bullet description.
   CRITICAL: Standalone "Achievements" sections MUST be extracted into 'awards'. NEVER omit achievements!
11. LANGUAGES:
   Extract all languages into the "languages" array:
   - 'name': Language name (e.g. "English", "Urdu", "Arabic").
   - 'fluency': Proficiency level (e.g. "Native", "Fluent", "Intermediate", "Beginner", or empty string).
12. Output raw JSON only. Do not wrap in markdown or explanation.
"""
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


def build_skill_category_map(raw_text: str):
    """
    Scans the raw resume text for explicit skills section headers and subcategories.
    E.g.
    Technical Skills: Python, SQL, ...
    Framworks & Libraries: Next.js, React.js, ...
    Tools: Git, Docker, ...
    
    Returns:
      (skill_to_cat_dict, list_of_detected_categories)
    """
    if not raw_text:
        return {}, []
    skill_to_cat = {}
    cat_headers = []
    
    # Locate skills section
    pattern = r'(?:TECHNICAL\s+SKILLS|SKILLS|CORE\s+COMPETENCIES|TECHNICAL\s+PROFICIENCIES)(.*?)(?:LANGUAGES|EXPERIENCE|EDUCATION|PROJECTS|AWARDS|CERTIFICATIONS|PUBLICATIONS|VOLUNTEER|$)'
    skills_sec = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
    sec_content = skills_sec.group(1) if skills_sec else raw_text
    
    current_cat = None
    for line in sec_content.split('\n'):
        line_s = line.strip()
        if not line_s:
            continue
        # Check for sub-header lines like "Category Name:" or "Category Name: skill1, skill2..."
        m = re.match(r'^([A-Za-z0-9\s&/\-_]+):\s*(.*)$', line_s)
        if m:
            cat_name = m.group(1).strip()
            # Ignore non-skill headers
            if cat_name.lower() not in ("email", "phone", "address", "date", "gpa", "degree", "title"):
                current_cat = normalize_skill_category(cat_name)
                if current_cat not in cat_headers:
                    cat_headers.append(current_cat)
                rest = m.group(2).strip()
                if rest:
                    for s in rest.split(','):
                        s_clean = s.strip()
                        if s_clean:
                            skill_to_cat[s_clean.lower()] = current_cat
        elif current_cat:
            for s in line_s.split(','):
                s_clean = s.strip()
                if s_clean:
                    skill_to_cat[s_clean.lower()] = current_cat
                    
    return skill_to_cat, cat_headers


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
    r'CERTIFICATIONS', r'CERTIFICATES', r'LICENSES(?:\s*&\s*CERTIFICATIONS)?', r'COURSES',
    r'AWARDS(?:\s*&\s*HONORS)?', r'HONORS(?:\s*&\s*AWARDS)?', r'ACHIEVEMENTS', r'KEY\s+ACHIEVEMENTS', r'AWARDS\s*&\s*ACHIEVEMENTS', r'ACCOMPLISHMENTS',
    r'LANGUAGES', r'LANGUAGE\s+PROFICIENCY',
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
    pattern = rf'(?:^|\n)\s*(?:{header_regex})\s*[:\n]+(.*?)(?=\n\s*(?:{KNOWN_HEADER_PATTERN})\s*[:\n]|\Z)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


DATE_RANGE_PATTERN = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4})\s*[-–—to]+\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}|\d{4}|Present|Current)'


def parse_raw_experience(raw_text: str) -> list[dict]:
    """
    Parses work experience directly from document raw text when LLM omits or drops the section.
    If no work experience section exists (e.g. student/new-grad resume), returns empty list [].
    """
    body = extract_section_raw(
        raw_text,
        r'WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT(?:\s+HISTORY)?|WORK\s+HISTORY|INTERNSHIPS|RELEVANT\s+EXPERIENCE|CAREER\s+HISTORY'
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



def parse_raw_certifications(raw_text: str) -> list[dict]:
    """
    Parses certifications directly from document raw text when LLM omits or drops them.
    """
    body = extract_section_raw(
        raw_text,
        r'CERTIFICATIONS|CERTIFICATES|LICENSES(?:\s*&\s*CERTIFICATIONS)?|COURSES(?:\s*&\s*CERTIFICATIONS)?'
    )
    if not body:
        return []
    certs = []
    seen = set()
    for line in body.split('\n'):
        l_clean = re.sub(r'^[•\-\*·\d\.\)]\s*', '', line).strip()
        if not l_clean or l_clean.upper() in ('CERTIFICATIONS', 'CERTIFICATES', 'LICENSES', 'COURSES'):
            continue
        # Pattern 1: Name - Issuer (Date) or Name | Issuer | Date
        m_dash = re.match(r'^(.*?)\s*[-–—|]\s*(.*?)(?:\s*[\(\[]([^\)\]]+)[\)\]])?$', l_clean)
        if m_dash and m_dash.group(1).strip() and m_dash.group(2).strip():
            name = m_dash.group(1).strip()
            issuer = m_dash.group(2).strip()
            date = (m_dash.group(3) or '').strip()
        else:
            # Pattern 2: Name (Date)
            m_date = re.search(r'\s*[\(\[]((?:19|20)\d{2}|[A-Za-z]{3,}\s+(?:19|20)\d{2})[\)\]]$', l_clean)
            if m_date:
                name = l_clean[:m_date.start()].strip()
                issuer = ''
                date = m_date.group(1).strip()
            else:
                name = l_clean
                issuer = ''
                date = ''

        if name and name.lower() not in seen:
            seen.add(name.lower())
            certs.append({
                "id": f"cert_{uuid.uuid4().hex[:8]}",
                "name": name,
                "issuer": issuer,
                "date": date,
                "expiry_date": ""
            })
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
        m_dash = re.match(r'^(.*?)\s*[-–—|]\s*(.*?)(?:\s*[\(\[]([^\)\]]+)[\)\]])?$', l_clean)
        if m_dash and m_dash.group(1).strip() and m_dash.group(2).strip():
            title = m_dash.group(1).strip()
            issuer = m_dash.group(2).strip()
            date = (m_dash.group(3) or '').strip()
        else:
            m_date = re.search(r'\s*[\(\[]((?:19|20)\d{2}|[A-Za-z]{3,}\s+(?:19|20)\d{2})[\)\]]$', l_clean)
            if m_date:
                title = l_clean[:m_date.start()].strip()
                issuer = ""
                date = m_date.group(1).strip()
            else:
                title = l_clean
                issuer = ""
                date = ""

        if title and title.lower() not in seen:
            seen.add(title.lower())
            awards.append({
                "id": f"award_{uuid.uuid4().hex[:8]}",
                "title": title,
                "issuer": issuer,
                "date": date,
                "description": ""
            })
    return awards


def parse_raw_languages(raw_text: str) -> list[dict]:
    """
    Parses languages directly from document raw text.
    """
    body = extract_section_raw(raw_text, r'LANGUAGES|LANGUAGE\s+PROFICIENCY')
    if not body:
        return []
    langs = []
    seen = set()
    parts = []
    for line in body.split('\n'):
        line_s = line.strip()
        if not line_s or line_s.upper() in ('LANGUAGES', 'LANGUAGE PROFICIENCY'):
            continue
        if ',' in line_s and not re.search(r'\([^\)]*,[^\)]*\)', line_s):
            parts.extend([p.strip() for p in line_s.split(',') if p.strip()])
        else:
            parts.append(line_s)

    for p in parts:
        p_clean = re.sub(r'^[•\-\*·\d\.\)]\s*', '', p).strip()
        if not p_clean:
            continue
        m = re.match(r'^(.*?)\s*[\(\-–]\s*([^\)]+)[\)]?$', p_clean)
        if m and m.group(1).strip() and m.group(2).strip():
            name = m.group(1).strip()
            fluency = m.group(2).strip()
        else:
            name = p_clean
            fluency = ""

        if name and name.lower() not in seen:
            seen.add(name.lower())
            langs.append({
                "id": f"lang_{uuid.uuid4().hex[:8]}",
                "name": name,
                "fluency": fluency
            })
    return langs


def post_process_json(parsed_json, raw_text: str = None):
    if not isinstance(parsed_json, dict):
        return parsed_json
        
    skill_to_cat = {}
    if raw_text:
        skill_to_cat, _ = build_skill_category_map(raw_text)

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
    if "skills" in parsed_json and isinstance(parsed_json["skills"], list):
        seen_skills = set()
        clean_skills = []
        for skill in parsed_json["skills"]:
            if isinstance(skill, dict):
                s_name = str(skill.get("name", "")).strip()
                if not s_name:
                    continue
                s_key = s_name.lower()
                if s_key in seen_skills:
                    continue
                seen_skills.add(s_key)

                cat = skill.get("category")
                if cat:
                    cat = str(cat).strip().rstrip(":")
                
                # If mapped from CV text, use the exact CV category header
                if s_name.lower() in skill_to_cat:
                    cat = skill_to_cat[s_name.lower()]
                elif not cat or cat.lower() in ("technical", "skills", "general"):
                    cat = skill_to_cat.get(s_name.lower()) or cat or "Technical Skills"
                
                cat = normalize_skill_category(cat)
                skill["name"] = s_name
                skill["category"] = cat
                if not skill.get("id"):
                    skill["id"] = f"skill_{uuid.uuid4().hex[:8]}"
                clean_skills.append(skill)
        parsed_json["skills"] = clean_skills

    # 2. Assign unique IDs to projects
    if "projects" in parsed_json and isinstance(parsed_json["projects"], list):
        for proj in parsed_json["projects"]:
            if isinstance(proj, dict) and not proj.get("id"):
                proj["id"] = f"proj_{uuid.uuid4().hex[:8]}"

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

    # 5. Clean & standardize CERTIFICATIONS (with raw_text fallback)
    certs = parsed_json.get("certifications")
    clean_certs = []
    seen_certs = set()
    if isinstance(certs, list) and len(certs) > 0:
        for c in certs:
            if isinstance(c, str) and c.strip():
                c_name = c.strip()
                if c_name.lower() not in seen_certs:
                    seen_certs.add(c_name.lower())
                    clean_certs.append({
                        "id": f"cert_{uuid.uuid4().hex[:8]}",
                        "name": c_name,
                        "issuer": "",
                        "date": "",
                        "expiry_date": ""
                    })
            elif isinstance(c, dict):
                c_name = (c.get("name") or c.get("title") or c.get("certification") or "").strip()
                if c_name and c_name.lower() not in seen_certs:
                    seen_certs.add(c_name.lower())
                    c["name"] = c_name
                    if not c.get("id"):
                        c["id"] = f"cert_{uuid.uuid4().hex[:8]}"
                    clean_certs.append(c)

    # Fallback to document text if certifications is still empty
    if not clean_certs and raw_text:
        fallback_certs = parse_raw_certifications(raw_text)
        if fallback_certs:
            clean_certs = fallback_certs

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

    # 7. Clean & standardize LANGUAGES (with raw_text fallback)
    langs = parsed_json.get("languages")
    clean_langs = []
    seen_langs = set()
    if isinstance(langs, list) and len(langs) > 0:
        for l in langs:
            if isinstance(l, str) and l.strip():
                m = re.match(r'^(.*?)\s*[\(\-–]\s*([^\)]+)[\)]?$', l.strip())
                l_name = m.group(1).strip() if m else l.strip()
                l_fluency = m.group(2).strip() if m else ""
                if l_name.lower() not in seen_langs:
                    seen_langs.add(l_name.lower())
                    clean_langs.append({
                        "id": f"lang_{uuid.uuid4().hex[:8]}",
                        "name": l_name,
                        "fluency": l_fluency
                    })
            elif isinstance(l, dict):
                l_name = (l.get("name") or l.get("language") or "").strip()
                if l_name and l_name.lower() not in seen_langs:
                    seen_langs.add(l_name.lower())
                    l["name"] = l_name
                    if not l.get("id"):
                        l["id"] = f"lang_{uuid.uuid4().hex[:8]}"
                    clean_langs.append(l)

    if not clean_langs and raw_text:
        fallback_langs = parse_raw_languages(raw_text)
        if fallback_langs:
            clean_langs = fallback_langs

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
        
    return parsed_json


def parse_resume_with_llm(text: str, photo: Optional[str] = None) -> ResumeData:
    """
    Parses resume text using Hugging Face Inference API with streaming token assembly.
    Using stream=True prevents 504 Gateway Timeouts by receiving tokens continuously.
    Supports candidate profile photo extracted from PDF.
    """
    system_prompt, user_prompt = _get_system_and_user_prompts(text)
    token = getattr(settings, "hf_token", None) or getattr(settings, "huggingface_token", None)

    last_error = None
    for model_name in SUPPORTED_MODELS:
        try:
            logger.info(f"Attempting streaming parse with model {model_name}...")
            client = InferenceClient(model=model_name, token=token, timeout=120.0)
            
            stream = client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
                temperature=0.1,
                stream=True,
            )
            
            chunks = []
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    chunks.append(chunk.choices[0].delta.content)
            
            raw_response = "".join(chunks)
            result_text = extract_json_from_text(raw_response)
            parsed_json = json.loads(result_text)
            parsed_json = post_process_json(parsed_json, raw_text=text)
            if photo:
                parsed_json["photo"] = photo
            cleaned_json = clean_dict(parsed_json)
            return ResumeData(**cleaned_json)
            
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt with {model_name} failed: {last_error}")

    raise ValueError(f"Failed to process the resume with AI models. Last error: {last_error}")


def stream_parse_resume_with_llm(text: str, photo: Optional[str] = None):
    """
    Generator yielding live progress events for real-time frontend feedback:
      - status stages (1 to 5)
      - token counts / chunks as generated
      - field and section updates as parsed
      - candidate profile photo if present
      - final validated resume payload
    """
    skill_to_cat, cat_headers = build_skill_category_map(text)
    system_prompt, user_prompt = _get_system_and_user_prompts(text)
    token = getattr(settings, "hf_token", None) or getattr(settings, "huggingface_token", None)

    yield {"event": "status", "stage": 1, "label": "Document read & structured text extracted", "pct": 5}

    if photo:
        yield {
            "event": "field_update",
            "field": "photo",
            "value": photo,
            "label": "Candidate Profile Photo",
            "pct": 8
        }

    last_error = None
    for model_name in SUPPORTED_MODELS:
        try:
            short_name = model_name.split("/")[-1]
            yield {"event": "status", "stage": 2, "label": f"Connected to {short_name} Neural Engine", "pct": 10}

            client = InferenceClient(model=model_name, token=token, timeout=120.0)
            stream = client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
                temperature=0.1,
                stream=True,
            )

            chunks = []
            chars_count = 0
            emitted_string_fields = set()
            emitted_sections = set()
            emitted_skills_count = 0
            emitted_skills_names = set()
            section_names = ["experience", "education", "projects", "certifications", "languages", "awards", "volunteer"]
            emitted_section_items_count = {s: 0 for s in section_names}
            emitted_section_items_keys = {s: set() for s in section_names}
            current_pct = 10

            def calc_progress() -> int:
                nonlocal current_pct
                # Tokens/chars contribution: nominal LLM JSON size is ~2500 characters
                char_part = min(35.0, (chars_count / 2500.0) * 35.0)
                # Single string fields (contact info, titles, summary): up to 15%
                field_part = min(15.0, len(emitted_string_fields) * 1.5)
                # Array sections item count: up to 20%
                items_count = sum(len(keys) for keys in emitted_section_items_keys.values())
                section_part = min(20.0, items_count * 2.5)
                # Individual skills parsed: up to 12%
                skill_part = min(12.0, len(emitted_skills_names) * 1.0)

                computed = int(10 + char_part + field_part + section_part + skill_part)
                current_pct = max(current_pct, min(92, computed))
                return current_pct

            string_fields = [
                "first_name", "last_name", "professional_title", "email", 
                "phone", "address", "location", "linkedin", "github", "portfolio", 
                "website", "summary"
            ]
            array_sections = section_names

            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
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
                                        if isinstance(val, str) and val.strip():
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
                            if s_name and s_name.lower() not in emitted_skills_names:
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

                    # Incremental extraction of ARRAY SECTION ITEMS (projects, experience, education, certs, awards, etc.) one by one
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

                        # Yield newly completed items one-by-one!
                        while emitted_section_items_count[section] < len(completed_items):
                            raw_item_obj = completed_items[emitted_section_items_count[section]]
                            emitted_section_items_count[section] += 1

                            processed_single = post_process_json({section: [raw_item_obj]}, raw_text=text)
                            cleaned_list = processed_single.get(section, [raw_item_obj])
                            if cleaned_list and len(cleaned_list) > 0:
                                cleaned_item = cleaned_list[0]
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

                        # When array closes (']'), emit section_update if not emitted yet
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
            if photo:
                parsed_json["photo"] = photo
            cleaned_json = clean_dict(parsed_json)
            validated = ResumeData(**cleaned_json)
            if photo and not validated.photo:
                validated.photo = photo

            # Emit section_update for any sections populated via fallback if not emitted during streaming
            for sec in ["experience", "education", "projects", "certifications", "languages", "awards", "volunteer"]:
                if sec not in emitted_sections and getattr(validated, sec, None):
                    emitted_sections.add(sec)
                    yield {
                        "event": "section_update",
                        "section": sec,
                        "data": [item.model_dump() for item in getattr(validated, sec)],
                        "label": f"Placed {len(getattr(validated, sec))} {sec.title()} items",
                        "pct": 98
                    }

            yield {
                "event": "complete",
                "stage": 5,
                "label": "Resume parsed successfully!",
                "pct": 100,
                "data": validated.model_dump()
            }
            return

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Streaming parse with {model_name} failed: {last_error}")

    yield {"event": "error", "stage": 0, "detail": f"AI Parsing failed: {last_error}", "pct": 0}


def optimize_bullet_with_llm(bullet: str, role: str = "", company: str = "", mode: str = "star") -> dict:
    """
    Transforms a bullet point into 3 high-impact STAR resume bullets with quantifiable metrics.
    Modes: 'star' (default), 'metrics', 'action_verbs'.
    """
    token = getattr(settings, "hf_token", None) or getattr(settings, "huggingface_token", None)
    
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
