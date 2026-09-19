"""Service for analyzing risks, notable clauses, and inconsistencies in legal documents."""

from typing import Any, Dict, Optional
from google import genai

from prompts.risk import (
    RISK_SCHEMA,
    RISK_SYSTEM_INSTRUCTION,
    build_risk_prompt,
)
from services.gemini_client import generate_json


def verify_quote_in_text(quote: str, source_text: str) -> bool:
    """Check if a quote appears verbatim in the source text, ignoring extra whitespace.

    Args:
        quote: The exact quote extracted by the model.
        source_text: The full source document text.

    Returns:
        True if the normalized quote appears in the normalized source text, False otherwise.
    """
    if not quote or not quote.strip():
        return False

    # Normalize whitespace (replace tabs, newlines, multiple spaces with a single space)
    normalized_quote = " ".join(quote.split()).lower()
    normalized_source = " ".join(source_text.split()).lower()

    return normalized_quote in normalized_source


def analyze_risks(
    document_text: str,
    client: Optional[genai.Client] = None,
) -> Dict[str, Any]:
    """Analyze risks and clauses in the provided document text.

    Also checks that every extracted quote actually appears in the source text,
    flagging any discrepancies as 'unverified'.

    Args:
        document_text: Plain text extracted from the document.
        client: Optional Gemini client (useful for testing/mocking).

    Returns:
        Dict containing overall_risk_score, inconsistencies, and clauses
        (each with a 'verification_status' of 'verified' or 'unverified').

    Raises:
        ValueError: If the document_text is empty or blank.
    """
    if not document_text or not document_text.strip():
        raise ValueError("Cannot analyze risks for an empty document.")

    prompt = build_risk_prompt(document_text)

    result = generate_json(
        prompt=prompt,
        schema=RISK_SCHEMA,
        system_instruction=RISK_SYSTEM_INSTRUCTION,
        client=client,
    )

    # Verify that each clause's exact_quote actually exists in the source text
    clauses = result.get("clauses", [])
    for clause in clauses:
        quote = clause.get("exact_quote", "")
        if verify_quote_in_text(quote, document_text):
            clause["verification_status"] = "verified"
        else:
            clause["verification_status"] = "unverified"

    return result
