"""Service for document Q&A and interactive chat."""

from typing import Any, Dict, List, Optional
from google import genai

from prompts.qa import (
    QA_SCHEMA,
    QA_SYSTEM_INSTRUCTION,
    build_qa_prompt,
)
from services.gemini_client import generate_json


def ask_question(
    document_text: str,
    question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    client: Optional[genai.Client] = None,
) -> Dict[str, Any]:
    """Answer a user question about a legal document strictly using document text.

    Args:
        document_text: Plain text extracted from the document.
        question: The user's question.
        chat_history: Optional list of previous chat messages ({role, content}).
                      Only the last 6 messages will be used for context.
        client: Optional Gemini client (useful for testing/mocking).

    Returns:
        Dict containing answer, supporting_quotes, confidence, and needs_lawyer.

    Raises:
        ValueError: If document_text or question is empty.
    """
    if not document_text or not document_text.strip():
        raise ValueError("Cannot answer questions without document text.")
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    # Keep only the last 6 messages for context
    recent_history = (chat_history or [])[-6:]

    prompt = build_qa_prompt(
        document_text=document_text,
        question=question.strip(),
        chat_history=recent_history,
    )

    return generate_json(
        prompt=prompt,
        schema=QA_SCHEMA,
        system_instruction=QA_SYSTEM_INSTRUCTION,
        client=client,
    )
