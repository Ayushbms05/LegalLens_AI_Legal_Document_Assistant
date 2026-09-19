"""Tests for the simplify_service module."""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from prompts.simplify import build_simplify_prompt
from services.simplify_service import simplify_document


def test_simplify_document_success():
    """Test successful document simplification with mocked Gemini client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "document_type": "Residential Lease Agreement",
        "one_paragraph_summary": "This is a 1-year rental lease between Apex Properties and Alex Johnson.",
        "key_points": [
            "Rent is $1,850/month due on the 1st.",
            "Late fee is $75 after the 5th.",
            "Security deposit is $1,850.",
            "No pets without written consent.",
            "Governed by Illinois law.",
        ],
        "jargon_glossary": [
            {"term": "Premises", "simple_meaning": "The apartment being rented."},
            {"term": "Escrow", "simple_meaning": "A safe holding account for the deposit."},
        ],
        "reading_level_used": "Simple",
    })
    mock_client.models.generate_content.return_value = mock_response

    sample_doc = "1. PARTIES: Apex Properties LLC and Alex Johnson. 2. RENT: $1,850/month."
    result = simplify_document(
        document_text=sample_doc,
        reading_level="Simple",
        language="English",
        client=mock_client,
    )

    assert result["document_type"] == "Residential Lease Agreement"
    assert len(result["key_points"]) == 5
    assert len(result["jargon_glossary"]) == 2
    assert result["reading_level_used"] == "Simple"
    assert mock_client.models.generate_content.call_count == 1


def test_simplify_document_empty_input():
    """Test that empty or whitespace-only document raises a ValueError."""
    with pytest.raises(ValueError, match="Cannot simplify an empty document"):
        simplify_document("")

    with pytest.raises(ValueError, match="Cannot simplify an empty document"):
        simplify_document("   \n\t  ")


def test_build_simplify_prompt_parameters():
    """Test that build_simplify_prompt includes reading level, language, and document text."""
    prompt = build_simplify_prompt(
        document_text="Contract text here",
        reading_level="Explain like I'm 15",
        language="Kannada",
    )

    assert "Explain like I'm 15" in prompt
    assert "Kannada" in prompt
    assert "Contract text here" in prompt
