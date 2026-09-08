# =============================================================================
# Professional Resume Builder — Security Utilities
# =============================================================================
"""
Security utilities for input sanitization, HTML escaping, and XSS prevention.

All user-supplied text should pass through sanitize_text() before storage
or rendering. File uploads are validated via validate_upload().
"""

import re
from typing import Optional

import bleach


# --- Allowed HTML tags/attributes for rich text fields (e.g., bullet points) ---
ALLOWED_TAGS: list[str] = [
    "p", "br", "strong", "em", "b", "i", "u",
    "ul", "ol", "li",
    "a", "span",
]

ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "a": ["href", "title", "target", "rel"],
    "span": ["class"],
}

# --- Allowed image MIME types for photo uploads ---
ALLOWED_IMAGE_TYPES: set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

# --- URL validation pattern ---
URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

# --- Email validation pattern ---
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# --- Phone validation pattern (international) ---
PHONE_PATTERN = re.compile(
    r"^\+?[\d\s\-\(\)\.]{7,20}$"
)


def sanitize_text(text: Optional[str], allow_html: bool = False) -> Optional[str]:
    """
    Sanitize user input text.

    Args:
        text: Raw user input string.
        allow_html: If True, allows a restricted subset of HTML tags
                    (for rich text fields like bullet points).
                    If False, strips ALL HTML tags.

    Returns:
        Sanitized string, or None if input is None.
    """
    if text is None:
        return None

    text = text.strip()

    if not text:
        return ""

    if allow_html:
        return bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,
        )
    else:
        # Strip all HTML and return plain text
        return bleach.clean(text, tags=[], strip=True)


def sanitize_url(url: Optional[str]) -> Optional[str]:
    """
    Sanitize and validate a URL.

    Returns the cleaned URL if valid, None otherwise.
    Only allows http:// and https:// schemes.
    """
    if not url:
        return None

    url = url.strip()

    if not url:
        return None

    # Auto-prepend https:// if no scheme provided
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Validate against pattern
    if URL_PATTERN.match(url):
        return bleach.clean(url, tags=[], strip=True)

    return None


def validate_email(email: Optional[str]) -> bool:
    """Validate an email address format."""
    if not email:
        return False
    return bool(EMAIL_PATTERN.match(email.strip()))


def validate_phone(phone: Optional[str]) -> bool:
    """Validate a phone number format (international)."""
    if not phone:
        return True  # Phone is optional
    return bool(PHONE_PATTERN.match(phone.strip()))


def validate_upload(
    content_type: Optional[str],
    file_size: int,
    max_size_bytes: int,
) -> tuple[bool, str]:
    """
    Validate a file upload.

    Args:
        content_type: MIME type of the uploaded file.
        file_size: Size in bytes.
        max_size_bytes: Maximum allowed size in bytes.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not content_type:
        return False, "File type could not be determined."

    if content_type not in ALLOWED_IMAGE_TYPES:
        allowed = ", ".join(ALLOWED_IMAGE_TYPES)
        return False, f"File type '{content_type}' is not allowed. Allowed: {allowed}"

    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        return False, f"File size exceeds maximum of {max_mb:.0f} MB."

    return True, ""


def escape_for_template(text: Optional[str]) -> str:
    """
    Escape text for safe inclusion in Jinja2 templates.

    This is a defense-in-depth measure — Jinja2 autoescaping should
    also be enabled, but this provides an extra layer of protection.
    """
    if not text:
        return ""
    return bleach.clean(text, tags=[], strip=True)
