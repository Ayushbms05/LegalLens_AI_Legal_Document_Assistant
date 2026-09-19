"""Security and sanitization utilities for LegalLens.

Provides input sanitization, prompt injection defense, XSS protection,
and error message masking.
"""

import html
import re
from typing import Optional


# Maximum allowed input lengths for DoS and memory protection
MAX_DOCUMENT_CHARS = 100_000
MAX_QUERY_CHARS = 1_000
MAX_FILENAME_CHARS = 255


def sanitize_input(text: Optional[str], max_length: int = MAX_DOCUMENT_CHARS) -> str:
    """Sanitize text input by removing control characters and enforcing length caps.

    Args:
        text: Raw input string.
        max_length: Maximum allowed character length.

    Returns:
        Sanitized, length-capped string.
    """
    if not text:
        return ""

    # Remove null bytes and non-printable control characters (except newline, tab, carriage return)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(text))

    # Cap length to prevent Denial of Service (DoS) / token exhaustion
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def wrap_untrusted_content(tag: str, content: str) -> str:
    """Wrap untrusted user or document text in XML-style boundary delimiters.

    Neutralizes delimiter injection attempts within the content.

    Args:
        tag: The boundary tag name (e.g. 'document_content', 'user_query').
        content: The untrusted content string.

    Returns:
        Content enclosed within safe boundary tags.
    """
    # Sanitize closing tag attempts to prevent boundary escape
    safe_content = content.replace(f"</{tag}>", f"<\\/{tag}>")
    return f"<{tag}>\n{safe_content}\n</{tag}>"


def sanitize_error_message(exc: Exception) -> str:
    """Mask internal system paths, URLs, and secrets before displaying errors to users.

    Args:
        exc: Caught exception.

    Returns:
        User-friendly, sanitized error message.
    """
    msg = str(exc)

    # Mask absolute file system paths (Unix / macOS / Windows)
    msg = re.sub(r"(?:/Users/[^\s:]+|/home/[^\s:]+|[A-Za-z]:\\[^\s:]+)", "[file_path]", msg)

    # Mask API keys if any accidentally leaked into message text
    msg = re.sub(r"(?:AIza[0-9A-Za-z_-]{30,}|AQ\.[0-9A-Za-z_-]{30,})", "[REDACTED_API_KEY]", msg)

    # Mask query parameters in URLs
    msg = re.sub(r"https?://[^\s?]+\?[^\s]+", "[url_with_parameters]", msg)

    # Clean whitespace
    clean_msg = " ".join(msg.split())
    return clean_msg if clean_msg else "An unexpected error occurred. Please try again."


def sanitize_html(text: Optional[str]) -> str:
    """Escape dynamic text to prevent Cross-Site Scripting (XSS).

    Args:
        text: Dynamic text to be rendered in HTML.

    Returns:
        HTML-escaped string.
    """
    if not text:
        return ""
    return html.escape(str(text), quote=True)
