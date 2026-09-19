"""Service for simplifying legal documents into plain English or regional languages."""

from typing import Any, Dict, Optional
from google import genai

from prompts.simplify import (
    SIMPLIFY_SCHEMA,
    SIMPLIFY_SYSTEM_INSTRUCTION,
    build_simplify_prompt,
)
from services.gemini_client import generate_json


def simplify_document(
    document_text: str,
    reading_level: str = "Simple",
    language: str = "English",
    client: Optional[genai.Client] = None,
) -> Dict[str, Any]:
    """Analyze and simplify the provided legal document text.

    Args:
        document_text: Plain text extracted from the document.
        reading_level: 'Simple' or 'Explain like I'm 15'.
        language: Language for the output ('English', 'Hindi', 'Kannada').
        client: Optional Gemini client (useful for dependency injection/testing).

    Returns:
        Dict containing document_type, one_paragraph_summary, key_points,
        jargon_glossary, and reading_level_used.

    Raises:
        ValueError: If the document_text is empty or blank.
    """
    if not document_text or not document_text.strip():
        raise ValueError("Cannot simplify an empty document.")

    prompt = build_simplify_prompt(
        document_text=document_text,
        reading_level=reading_level,
        language=language,
    )

    return generate_json(
        prompt=prompt,
        schema=SIMPLIFY_SCHEMA,
        system_instruction=SIMPLIFY_SYSTEM_INSTRUCTION,
        client=client,
    )
