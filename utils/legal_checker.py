"""Utility for checking if uploaded text resembles a legal document."""

import re

# Common legal terminology and keywords found in contracts, leases, and agreements
LEGAL_KEYWORDS = [
    r"\bagreement\b",
    r"\bcontract\b",
    r"\blease\b",
    r"\bpart(y|ies)\b",
    r"\bclause\b",
    r"\bsection\b",
    r"\bterms?\b",
    r"\bconditions?\b",
    r"\bshall\b",
    r"\bliabilit(y|ies)\b",
    r"\bterminat(e|ion)\b",
    r"\bhereby\b",
    r"\bgoverning law\b",
    r"\bindemnif\w*\b",
    r"\bwarrant\w*\b",
    r"\bsignatur\w*\b",
    r"\btenant\b",
    r"\blandlord\b",
    r"\bemployer\b",
    r"\bemployee\b",
    r"\bconfidential\w*\b",
    r"\bjurisdiction\b",
    r"\bherein\b",
    r"\bwhereas\b",
]


def is_likely_legal_document(text: str, min_keyword_matches: int = 3) -> bool:
    """Check if the provided text contains typical legal terminology.

    Args:
        text: Plain text to inspect.
        min_keyword_matches: Minimum number of unique legal keywords required (default: 3).

    Returns:
        True if at least min_keyword_matches unique legal terms are found, False otherwise.
    """
    if not text or not text.strip():
        return False

    lowered = text.lower()
    matches = sum(1 for pattern in LEGAL_KEYWORDS if re.search(pattern, lowered))
    return matches >= min_keyword_matches
