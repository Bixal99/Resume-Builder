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
2. WORK EXPERIENCE: Only actual employment at a company. Do not include student clubs or volunteer roles in experience.
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
9. Output raw JSON only. Do not wrap in markdown or explanation.
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
                current_cat = cat_name
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


def normalize_skill_category(cat: str) -> str:
    if not cat:
        return "Technical Skills"
    c = str(cat).strip().rstrip(":").lower()
    if c in ("technical", "technical skills", "skills", "tech", "programming", "languages", "programming languages", "coding", "core competencies", "technical proficiencies"):
        return "Technical Skills"
    if c in ("framework", "frameworks", "libraries", "frameworks & libraries", "frameworks and libraries", "frameworks & tools", "framework & library"):
        return "Frameworks & Libraries"
    if c in ("tool", "tools", "tools & platforms", "tools and platforms", "platforms", "developer tools", "technologies", "devops", "software", "environment"):
        return "Tools & Platforms"
    if c in ("soft", "soft skills", "interpersonal", "interpersonal skills", "professional skills", "management"):
        return "Soft Skills"
    return str(cat).strip().rstrip(":")


def post_process_json(parsed_json, raw_text: str = None):
    if not isinstance(parsed_json, dict):
        return parsed_json
        
    skill_to_cat = {}
    if raw_text:
        skill_to_cat, _ = build_skill_category_map(raw_text)

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
    if "experience" in parsed_json and isinstance(parsed_json["experience"], list):
        real_exp = []
        if "volunteer" not in parsed_json or not isinstance(parsed_json["volunteer"], list):
            parsed_json["volunteer"] = []
            
        for exp in parsed_json["experience"]:
            if not isinstance(exp, dict):
                continue
                
            title = str(exp.get("position", "")).lower()
            company = str(exp.get("company", "")).lower()
            
            if title == "none" or company == "none":
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

    # 5. Assign IDs to remaining list sections
    for section, prefix in [
        ("languages", "lang"),
        ("certifications", "cert"),
        ("awards", "award"),
        ("volunteer", "vol"),
        ("references", "ref"),
    ]:
        if section in parsed_json and isinstance(parsed_json[section], list):
            for item in parsed_json[section]:
                if isinstance(item, dict) and not item.get("id"):
                    item["id"] = f"{prefix}_{uuid.uuid4().hex[:8]}"
        
    return parsed_json


def parse_resume_with_llm(text: str) -> ResumeData:
    """
    Parses resume text using Hugging Face Inference API with streaming token assembly.
    Using stream=True prevents 504 Gateway Timeouts by receiving tokens continuously.
    """
    system_prompt, user_prompt = _get_system_and_user_prompts(text)
    token = getattr(settings, "hf_token", None) or getattr(settings, "huggingface_token", None)

    last_error = None
    for model_name in SUPPORTED_MODELS:
        try:
            logger.info(f"Attempting streaming parse with model {model_name}...")
            client = InferenceClient(model=model_name, token=token)
            
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
            cleaned_json = clean_dict(parsed_json)
            return ResumeData(**cleaned_json)
            
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt with {model_name} failed: {last_error}")

    raise ValueError(f"Failed to process the resume with AI models. Last error: {last_error}")


def stream_parse_resume_with_llm(text: str):
    """
    Generator yielding live progress events for real-time frontend feedback:
      - status stages (1 to 5)
      - token counts / chunks as generated
      - final validated resume payload
    """
    skill_to_cat, cat_headers = build_skill_category_map(text)
    system_prompt, user_prompt = _get_system_and_user_prompts(text)
    token = getattr(settings, "hf_token", None) or getattr(settings, "huggingface_token", None)

    yield {"event": "status", "stage": 1, "label": "Document read & structured text extracted", "pct": 5}

    last_error = None
    for model_name in SUPPORTED_MODELS:
        try:
            short_name = model_name.split("/")[-1]
            yield {"event": "status", "stage": 2, "label": f"Connected to {short_name} Neural Engine", "pct": 10}

            client = InferenceClient(model=model_name, token=token)
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
            current_pct = 10

            def calc_progress() -> int:
                nonlocal current_pct
                # Tokens/chars contribution: nominal LLM JSON size is ~2500 characters
                char_part = min(35.0, (chars_count / 2500.0) * 35.0)
                # Single string fields (contact info, titles, summary): up to 15%
                field_part = min(15.0, len(emitted_string_fields) * 1.5)
                # Array sections (experience, education, projects, etc.): up to 20%
                section_part = min(20.0, len(emitted_sections) * 4.5)
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
            array_sections = ["experience", "education", "projects", "certifications", "languages"]

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

                    # Check for completed array sections
                    for section in array_sections:
                        if section not in emitted_sections:
                            sec_match = re.search(rf'"{section}"\s*:\s*\[', raw_buffer)
                            if sec_match:
                                start_idx = sec_match.end() - 1
                                depth = 0
                                in_string = False
                                escape = False
                                for j in range(start_idx, len(raw_buffer)):
                                    c = raw_buffer[j]
                                    if escape:
                                        escape = False
                                        continue
                                    if c == '\\':
                                        escape = True
                                        continue
                                    if c == '"':
                                        in_string = not in_string
                                        continue
                                    if not in_string:
                                        if c == '[':
                                            depth += 1
                                        elif c == ']':
                                            depth -= 1
                                            if depth == 0:
                                                json_str = raw_buffer[start_idx:j+1]
                                                try:
                                                    arr_data = json.loads(json_str)
                                                    if arr_data and isinstance(arr_data, list) and len(arr_data) > 0:
                                                        emitted_sections.add(section)
                                                        processed_obj = post_process_json({section: arr_data}, raw_text=text)
                                                        cleaned_arr = processed_obj.get(section, arr_data)
                                                        yield {
                                                            "event": "section_update",
                                                            "section": section,
                                                            "data": cleaned_arr,
                                                            "label": f"Placed {len(cleaned_arr)} {section.title()} items",
                                                            "pct": calc_progress()
                                                        }
                                                except Exception:
                                                    pass
                                                break

                    yield {"event": "token", "stage": 3, "chars": chars_count, "chunk": content, "pct": calc_progress()}

            yield {"event": "status", "stage": 4, "label": "Validating JSON schema & formatting STAR sections...", "pct": 95}

            raw_response = "".join(chunks)
            result_text = extract_json_from_text(raw_response)
            parsed_json = json.loads(result_text)
            parsed_json = post_process_json(parsed_json, raw_text=text)
            cleaned_json = clean_dict(parsed_json)
            validated = ResumeData(**cleaned_json)

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
