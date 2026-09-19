"""Prompts and schemas for the Action Plan tab."""

from typing import Any, Dict

# JSON Schema for action plan structured output from Gemini
ACTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "checklist_before_signing": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Essential items, clauses, or inspections the signer should verify before signing.",
        },
        "obligations_and_deadlines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "what": {
                        "type": "string",
                        "description": "The specific obligation or requirement.",
                    },
                    "who": {
                        "type": "string",
                        "description": "The party responsible (e.g. Tenant, Landlord, Employee).",
                    },
                    "when": {
                        "type": "string",
                        "description": "The deadline, timeframe, or frequency (e.g. 1st of every month, within 5 days).",
                    },
                },
                "required": ["what", "who", "when"],
            },
            "description": "Key duties, obligations, and deadlines extracted from the document.",
        },
        "questions_for_a_lawyer": {
            "type": "array",
            "items": {"type": "string"},
            "description": "8 to 10 specific, targeted questions for a lawyer regarding ambiguities, risks, or rights.",
        },
        "possible_next_steps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Practical next steps for the signer (e.g., negotiating terms, requesting amendments).",
        },
        "documents_to_gather": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Important records, photos, receipts, or documents the signer should collect and keep.",
        },
    },
    "required": [
        "checklist_before_signing",
        "obligations_and_deadlines",
        "questions_for_a_lawyer",
        "possible_next_steps",
        "documents_to_gather",
    ],
}

# System prompt enforcing strict grounding and non-advice framing
ACTION_SYSTEM_INSTRUCTION = (
    "You are LegalLens, an educational AI assistant that creates practical, organized action plans "
    "from legal documents.\n\n"
    "CRITICAL GROUNDING RULES:\n"
    "1. Base all checklist items, obligations, deadlines, and required documents strictly on the provided text.\n"
    "2. If a deadline or obligation is not specified in the document, state 'Not specified in the document'.\n"
    "3. Provide exactly 8 to 10 specific, targeted questions for a qualified lawyer to help the user understand "
    "their rights or clarify potential ambiguities in this specific agreement.\n"
    "4. You provide legal INFORMATION only, never legal advice.\n"
    "5. Return strictly valid JSON conforming to the schema."
)


def build_action_prompt(document_text: str) -> str:
    """Build the prompt for generating an action plan.

    Args:
        document_text: Plain text of the legal document.

    Returns:
        Formatted prompt string.
    """
    return f"""Please generate a comprehensive, structured Action Plan based on the following legal document.

Requirements:
1. checklist_before_signing: A list of key verification items to check before signing.
2. obligations_and_deadlines: A list of objects with 'what' (the duty), 'who' (responsible party), and 'when' (deadline/frequency).
3. questions_for_a_lawyer: Exactly 8 to 10 specific, insightful questions the signer can ask a lawyer before signing.
4. possible_next_steps: Practical steps for the signer (e.g., inspections, negotiations, clarifying ambiguous terms).
5. documents_to_gather: Records, proof of payments, or attachments the signer should prepare or keep.

DOCUMENT TEXT:
\"\"\"
{document_text}
\"\"\"
"""
