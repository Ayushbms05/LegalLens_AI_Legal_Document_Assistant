"""Service for comparing two legal documents or contract versions."""

from typing import Any, Dict, List, Optional
from google import genai

from prompts.compare import (
    COMPARE_SCHEMA,
    COMPARE_SYSTEM_INSTRUCTION,
    build_compare_prompt,
)
from services.gemini_client import generate_json


def compare_documents(
    doc_a_text: str,
    doc_b_text: str,
    client: Optional[genai.Client] = None,
    max_chars: int = 30000,
) -> Dict[str, Any]:
    """Compare two legal documents and highlight differences, favorability, and missing clauses.

    Handles very long documents by truncating to max_chars per document and recording warnings.

    Args:
        doc_a_text: Plain text of Document A.
        doc_b_text: Plain text of Document B.
        client: Optional Gemini client (useful for testing/mocking).
        max_chars: Maximum characters allowed per document before truncating (default: 30,000).

    Returns:
        Dict containing differences, missing_clauses_in_each,
        overall_recommendation_for_signer, and truncation_warnings.

    Raises:
        ValueError: If either document text is empty.
    """
    if not doc_a_text or not doc_a_text.strip():
        raise ValueError("Document A cannot be empty.")
    if not doc_b_text or not doc_b_text.strip():
        raise ValueError("Document B cannot be empty.")

    warnings_list: List[str] = []

    # Check and handle truncation for Document A
    cleaned_a = doc_a_text.strip()
    if len(cleaned_a) > max_chars:
        cleaned_a = cleaned_a[:max_chars]
        warnings_list.append(
            f"Document A was truncated from {len(doc_a_text):,} to {max_chars:,} characters "
            "to ensure optimal comparison performance."
        )

    # Check and handle truncation for Document B
    cleaned_b = doc_b_text.strip()
    if len(cleaned_b) > max_chars:
        cleaned_b = cleaned_b[:max_chars]
        warnings_list.append(
            f"Document B was truncated from {len(doc_b_text):,} to {max_chars:,} characters "
            "to ensure optimal comparison performance."
        )

    prompt = build_compare_prompt(cleaned_a, cleaned_b)

    result = generate_json(
        prompt=prompt,
        schema=COMPARE_SCHEMA,
        system_instruction=COMPARE_SYSTEM_INSTRUCTION,
        client=client,
    )

    # Attach any truncation warnings so the UI can display them
    result["truncation_warnings"] = warnings_list

    return result
