"""Prompts and schemas for the Compare tab."""

from typing import Any, Dict

# JSON Schema for comparison structured output from Gemini
COMPARE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "differences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Subject or clause category, e.g. Rent, Late Fee, Security Deposit, Pet Policy.",
                    },
                    "document_a_says": {
                        "type": "string",
                        "description": "Summary or quote of what Document A specifies for this topic.",
                    },
                    "document_b_says": {
                        "type": "string",
                        "description": "Summary or quote of what Document B specifies for this topic.",
                    },
                    "which_is_more_favorable_to_signer": {
                        "type": "string",
                        "enum": ["A", "B", "Neither"],
                        "description": "Which version is more advantageous to the signing party (e.g., tenant/employee).",
                    },
                    "impact_explanation": {
                        "type": "string",
                        "description": "Detailed explanation of why this difference matters and its financial or legal impact.",
                    },
                },
                "required": [
                    "topic",
                    "document_a_says",
                    "document_b_says",
                    "which_is_more_favorable_to_signer",
                    "impact_explanation",
                ],
            },
            "description": "List of key differences between Document A and Document B.",
        },
        "missing_clauses_in_each": {
            "type": "object",
            "properties": {
                "missing_in_a": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Clauses or requirements present in Document B but completely absent in Document A.",
                },
                "missing_in_b": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Clauses or requirements present in Document A but completely absent in Document B.",
                },
            },
            "required": ["missing_in_a", "missing_in_b"],
        },
        "overall_recommendation_for_signer": {
            "type": "string",
            "description": "Short neutral summary of which document is overall more favorable from an educational perspective.",
        },
    },
    "required": ["differences", "missing_clauses_in_each", "overall_recommendation_for_signer"],
}

# System prompt enforcing strict grounding and non-advice framing
COMPARE_SYSTEM_INSTRUCTION = (
    "You are LegalLens, an educational AI assistant that compares legal documents.\n\n"
    "CRITICAL GROUNDING RULES:\n"
    "1. Compare ONLY the explicit terms provided in Document A and Document B.\n"
    "2. Do NOT invent differences or assume terms that are not written in the texts.\n"
    "3. If a clause or topic is absent in one document, state 'Not specified' for that document.\n"
    "4. Assess favorability strictly from the signer's perspective (e.g. tenant, borrower, employee).\n"
    "5. Provide legal INFORMATION, never legal advice.\n"
    "6. Return strictly valid JSON conforming to the schema."
)


def build_compare_prompt(doc_a_text: str, doc_b_text: str) -> str:
    """Build the prompt comparing Document A and Document B.

    Args:
        doc_a_text: Plain text of Document A.
        doc_b_text: Plain text of Document B.

    Returns:
        Formatted prompt string.
    """
    return f"""Please compare the following two versions of a legal document.

DOCUMENT A:
\"\"\"
{doc_a_text}
\"\"\"

DOCUMENT B:
\"\"\"
{doc_b_text}
\"\"\"

Requirements:
1. differences: Identify every major difference in terms, costs, timelines, rights, or penalties. For each, specify:
   - topic (e.g. Rent Amount, Late Fees, Pet Policy)
   - document_a_says
   - document_b_says
   - which_is_more_favorable_to_signer ('A', 'B', or 'Neither')
   - impact_explanation (practical impact on the signer)
2. missing_clauses_in_each:
   - missing_in_a: terms in B that are absent in A
   - missing_in_b: terms in A that are absent in B
3. overall_recommendation_for_signer: A short summary of which version is more favorable to the signer and why.
"""
