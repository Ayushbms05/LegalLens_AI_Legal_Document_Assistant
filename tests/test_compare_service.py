"""Tests for the compare_service module."""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from services.compare_service import compare_documents


def test_compare_documents_success():
    """Test successful comparison between two documents with mocked client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "differences": [
            {
                "topic": "Monthly Rent",
                "document_a_says": "$1,850/month",
                "document_b_says": "$2,000/month",
                "which_is_more_favorable_to_signer": "A",
                "impact_explanation": "Version A saves $150 per month ($1,800 annually).",
            }
        ],
        "missing_clauses_in_each": {
            "missing_in_a": ["Professional carpet cleaning requirement"],
            "missing_in_b": [],
        },
        "overall_recommendation_for_signer": "Version A is significantly more favorable due to lower rent and deposit.",
    })
    mock_client.models.generate_content.return_value = mock_response

    doc_a = "Rent is $1,850."
    doc_b = "Rent is $2,000. Tenant pays carpet cleaning."

    result = compare_documents(doc_a, doc_b, client=mock_client)

    assert len(result["differences"]) == 1
    assert result["differences"][0]["which_is_more_favorable_to_signer"] == "A"
    assert result["truncation_warnings"] == []
    assert len(result["missing_clauses_in_each"]["missing_in_a"]) == 1


def test_compare_documents_truncation_warning():
    """Test that documents exceeding max_chars are truncated and produce visible warnings."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "differences": [],
        "missing_clauses_in_each": {"missing_in_a": [], "missing_in_b": []},
        "overall_recommendation_for_signer": "Equal terms.",
    })
    mock_client.models.generate_content.return_value = mock_response

    long_doc_a = "A" * 2000
    long_doc_b = "B" * 2500

    # Set max_chars = 1000 to trigger truncation
    result = compare_documents(long_doc_a, long_doc_b, client=mock_client, max_chars=1000)

    assert len(result["truncation_warnings"]) == 2
    assert "Document A was truncated from 2,000 to 1,000" in result["truncation_warnings"][0]
    assert "Document B was truncated from 2,500 to 1,000" in result["truncation_warnings"][1]

    # Verify that prompt received only the truncated text
    call_args = mock_client.models.generate_content.call_args
    prompt_sent = call_args.kwargs.get("contents") or call_args[1].get("contents")
    assert "A" * 1001 not in prompt_sent
    assert "B" * 1001 not in prompt_sent


def test_compare_documents_empty_inputs():
    """Test that empty inputs raise ValueError."""
    with pytest.raises(ValueError, match="Document A cannot be empty"):
        compare_documents("", "Doc B text")

    with pytest.raises(ValueError, match="Document B cannot be empty"):
        compare_documents("Doc A text", "")
