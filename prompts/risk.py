"""Prompts and schemas for the Risks tab."""

from typing import Any, Dict

# JSON Schema for risk analysis output from Gemini
RISK_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "overall_risk_score": {
            "type": "integer",
            "description": "An overall risk score between 0 (very low risk, standard terms) and 100 (extreme risk, highly one-sided).",
        },
        "inconsistencies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Places where the document contradicts itself or conflicts with itself. Return an empty list if none found.",
        },
        "clauses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "clause_title": {
                        "type": "string",
                        "description": "Short descriptive title of the clause.",
                    },
                    "exact_quote": {
                        "type": "string",
                        "description": "Exact verbatim quote copied directly from the document text.",
                    },
                    "plain_explanation": {
                        "type": "string",
                        "description": "Plain English explanation of what this clause means.",
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "Payment",
                            "Termination",
                            "Liability",
                            "Privacy",
                            "Penalty",
                            "Renewal",
                            "Other",
                        ],
                        "description": "Category of the clause.",
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High"],
                        "description": "Assessed risk level for this clause.",
                    },
                    "why_it_matters": {
                        "type": "string",
                        "description": "Why this clause is significant to the signing party.",
                    },
                    "suggested_question_to_ask": {
                        "type": "string",
                        "description": "A practical question the reader can ask before signing.",
                    },
                },
                "required": [
                    "clause_title",
                    "exact_quote",
                    "plain_explanation",
                    "category",
                    "risk_level",
                    "why_it_matters",
                    "suggested_question_to_ask",
                ],
            },
            "description": "List of analyzed clauses highlighting notable obligations or risks.",
        },
    },
    "required": ["overall_risk_score", "inconsistencies", "clauses"],
}

# System instruction enforcing strict factual grounding, coverage, and non-advice framing
RISK_SYSTEM_INSTRUCTION = (
    "You are LegalLens, an educational AI assistant that identifies notable clauses, "
    "obligations, and risks in legal documents. You provide legal INFORMATION only, never legal advice.\n\n"
    "RULES FOR RISK & CLAUSE ANALYSIS:\n"
    "1. Coverage: Return EVERY clause that involves money, deadlines, penalties, renewal, "
    "termination or notice, access or privacy, liability, subletting, or dispute resolution. "
    "For a normal 2-page contract that is usually 10 to 15 clauses. Include Low-risk clauses too, "
    "marked Low. Do not skip a clause because a similar one is already listed.\n"
    "2. Always check for automatic renewal clauses, and for deposit size, refund conditions and deductions. "
    "Analyse each as its own clause.\n"
    "3. Wording of why_it_matters and plain_explanation: Describe the practical effect on the person signing "
    '("This means you could...", "People often ask to change this..."). Do NOT state legal conclusions such as '
    '"this violates your rights", "this is illegal" or "this is unenforceable". Do NOT state market rates or '
    'legal norms as facts. If you mention what is common, say "often" and suggest checking with a lawyer.\n'
    "4. Inconsistencies: List only pairs of clauses that answer the SAME question with DIFFERENT values "
    "(for example two different notice periods or two different refund deadlines). Name both clause numbers "
    "and both values. Do not include clauses that cover a different topic.\n"
    "5. Keep every exact_quote character for character from the document. Do NOT rephrase or paraphrase the quote.\n"
    "6. Return strictly valid JSON conforming to the schema."
)


def build_risk_prompt(document_text: str) -> str:
    """Build the prompt for analyzing legal document risks.

    Args:
        document_text: The plain text of the legal document.

    Returns:
        Formatted prompt string.
    """
    return f"""Please perform a thorough risk and clause analysis of the following legal document.

Requirements:
1. overall_risk_score: A score from 0 (very low risk / standard terms) to 100 (high risk / heavily one-sided).
2. inconsistencies: Any contradictory clauses (e.g. conflicting notice periods or mismatched dates). If none, return [].
3. clauses: Identify notable clauses across the document. For each clause provide:
   - clause_title: Descriptive name (e.g. "Late Payment Fee", "Automatic Renewal").
   - exact_quote: EXACT verbatim snippet from the document text below.
   - plain_explanation: What it means in plain English.
   - category: One of "Payment", "Termination", "Liability", "Privacy", "Penalty", "Renewal", "Other".
   - risk_level: "Low", "Medium", or "High".
   - why_it_matters: Why the signing party should care.
   - suggested_question_to_ask: A question to clarify or negotiate this clause.

DOCUMENT TEXT:
\"\"\"
{document_text}
\"\"\"
"""
