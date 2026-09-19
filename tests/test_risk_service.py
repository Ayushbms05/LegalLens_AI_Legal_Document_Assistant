"""Tests for the risk_service module and quote verification."""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from services.risk_service import analyze_risks, verify_quote_in_text


def test_verify_quote_in_text():
    """Test quote verification with exact and whitespace-varying quotes."""
    source = "Tenant agrees to pay monthly rent of $1,850 on the 1st of each month."

    # Exact match
    assert verify_quote_in_text("monthly rent of $1,850", source) is True

    # Whitespace/case variations
    assert verify_quote_in_text("  Monthly   Rent Of  $1,850 \n", source) is True

    # Quote not in source
    assert verify_quote_in_text("Tenant must pay $5,000 immediately", source) is False
    assert verify_quote_in_text("", source) is False


def test_analyze_risks_quote_verification():
    """Test analyze_risks marks present quotes as 'verified' and missing quotes as 'unverified'."""
    source_text = "Late fee of $75.00 shall be assessed after the fifth day."

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "overall_risk_score": 45,
        "inconsistencies": [],
        "clauses": [
            {
                "clause_title": "Late Fee",
                "exact_quote": "Late fee of $75.00 shall be assessed",
                "plain_explanation": "You get charged $75 if late.",
                "category": "Penalty",
                "risk_level": "Medium",
                "why_it_matters": "Adds recurring cost if payment is delayed.",
                "suggested_question_to_ask": "Can the grace period be extended?",
            },
            {
                "clause_title": "Hallucinated Clause",
                "exact_quote": "Tenant forfeits all possessions upon one day notice",
                "plain_explanation": "This clause does not exist in the source.",
                "category": "Liability",
                "risk_level": "High",
                "why_it_matters": "Extremely punitive.",
                "suggested_question_to_ask": "Why is this here?",
            },
        ],
    })
    mock_client.models.generate_content.return_value = mock_response

    result = analyze_risks(source_text, client=mock_client)

    assert result["overall_risk_score"] == 45
    clauses = result["clauses"]
    assert len(clauses) == 2

    # First quote exists in source_text -> verified
    assert clauses[0]["verification_status"] == "verified"

    # Second quote does not exist -> unverified
    assert clauses[1]["verification_status"] == "unverified"


def test_analyze_risks_empty_document():
    """Test that empty document raises ValueError."""
    with pytest.raises(ValueError, match="Cannot analyze risks for an empty document"):
        analyze_risks("")
