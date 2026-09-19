"""Service for generating post-analysis action plans, checklists, and lawyer questions."""

from typing import Any, Dict, Optional
from google import genai

from prompts.action import (
    ACTION_SCHEMA,
    ACTION_SYSTEM_INSTRUCTION,
    build_action_prompt,
)
from services.gemini_client import generate_json


def generate_action_plan(
    document_text: str,
    client: Optional[genai.Client] = None,
) -> Dict[str, Any]:
    """Generate a structured action plan from a legal document.

    Args:
        document_text: Plain text extracted from the document.
        client: Optional Gemini client (useful for testing/mocking).

    Returns:
        Dict containing checklist_before_signing, obligations_and_deadlines,
        questions_for_a_lawyer, possible_next_steps, and documents_to_gather.

    Raises:
        ValueError: If document_text is empty or blank.
    """
    if not document_text or not document_text.strip():
        raise ValueError("Cannot generate an action plan for an empty document.")

    prompt = build_action_prompt(document_text)

    return generate_json(
        prompt=prompt,
        schema=ACTION_SCHEMA,
        system_instruction=ACTION_SYSTEM_INSTRUCTION,
        client=client,
    )
