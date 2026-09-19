"""Prompts and schemas for the Ask (Q&A) tab."""

from typing import Any, Dict, List, Optional

# JSON schema for Q&A structured response from Gemini
QA_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "Clear plain-language answer to the user's question, grounded strictly in the document.",
        },
        "supporting_quotes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of verbatim quotes from the document that directly support this answer.",
        },
        "confidence": {
            "type": "string",
            "enum": ["High", "Medium", "Low"],
            "description": "Confidence level based on clarity and presence in the document.",
        },
        "needs_lawyer": {
            "type": "boolean",
            "description": "True if the question touches on matters outside the document, significant ambiguities, or requires legal counsel.",
        },
    },
    "required": ["answer", "supporting_quotes", "confidence", "needs_lawyer"],
}

# System prompt enforcing factual grounding, non-advice framing, and lawyer escalation
QA_SYSTEM_INSTRUCTION = (
    "You are LegalLens, an educational AI assistant that answers questions about legal documents.\n\n"
    "CRITICAL GROUNDING RULES:\n"
    "1. Answer ONLY from the provided document text.\n"
    "2. Quote the relevant clause or clauses verbatim in 'supporting_quotes'.\n"
    "3. If the answer is NOT in the document, your answer MUST explicitly state: "
    "'The document doesn't cover this' and suggest what specific question to ask a qualified lawyer.\n"
    "4. If the question requires legal strategy, evaluation of enforceability, or advice beyond factual reading, "
    "set 'needs_lawyer' to true.\n"
    "5. Provide legal INFORMATION, never legal advice.\n"
    "6. Return strictly valid JSON adhering to the schema."
)


def build_qa_prompt(
    document_text: str,
    question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Build the prompt for the Q&A service, including up to 6 recent messages.

    Args:
        document_text: Plain text of the legal document.
        question: The user's question.
        chat_history: Optional list of previous chat messages.

    Returns:
        Formatted prompt string.
    """
    history_text = ""
    if chat_history:
        # Keep up to the last 6 messages
        recent = chat_history[-6:]
        lines = []
        for msg in recent:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        history_text = "CONVERSATION HISTORY:\n" + "\n".join(lines) + "\n\n"

    return f"""{history_text}DOCUMENT TEXT:
\"\"\"
{document_text}
\"\"\"

USER QUESTION:
{question}

Please answer the question based strictly on the document text provided above.
"""
