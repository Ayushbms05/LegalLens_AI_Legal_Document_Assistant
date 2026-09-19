"""Tests for the doc_exporter utility."""

import io
from pathlib import Path
import sys
from docx import Document
import pytest

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from utils.doc_exporter import export_to_docx


def test_export_to_docx_creates_and_opens():
    """Test that export_to_docx creates a valid Word document that opens without errors."""
    summary_data = {
        "document_type": "Residential Lease Agreement",
        "one_paragraph_summary": "A 1-year lease agreement for an apartment.",
        "key_points": ["Rent is $1,850 due on the 1st.", "Late fee is $75."],
        "jargon_glossary": [{"term": "Premises", "simple_meaning": "The apartment."}],
    }
    risks_data = {
        "overall_risk_score": 40,
        "inconsistencies": ["Contradictory notice dates."],
        "clauses": [
            {
                "clause_title": "Late Fee",
                "exact_quote": "Late fee of $75.00",
                "plain_explanation": "Charged if late.",
                "category": "Penalty",
                "risk_level": "Medium",
                "why_it_matters": "Financial cost.",
                "suggested_question_to_ask": "Is there a grace period?",
            }
        ],
    }
    action_data = {
        "checklist_before_signing": ["Verify condition of premises."],
        "obligations_and_deadlines": [{"what": "Pay rent", "who": "Tenant", "when": "1st"}],
        "questions_for_a_lawyer": ["Is the deposit escrow compliant?"],
        "possible_next_steps": ["Inspect the unit."],
        "documents_to_gather": ["Signed agreement copy."],
    }

    # Generate document buffer
    buffer = export_to_docx(
        summary_data=summary_data,
        risks_data=risks_data,
        action_data=action_data,
        doc_name="Sample Lease",
    )

    # Verify buffer is not empty
    assert buffer is not None
    assert buffer.getvalue()

    # Verify that python-docx can open and read the file
    doc = Document(buffer)
    paragraphs_text = [p.text for p in doc.paragraphs if p.text]

    # Check title and headings exist
    assert any("LegalLens Analysis Report: Sample Lease" in t for t in paragraphs_text)
    assert any("DISCLAIMER" in t for t in paragraphs_text)
    assert any("1. Document Summary" in t for t in paragraphs_text)
    assert any("2. Risk & Clause Analysis" in t for t in paragraphs_text)
    assert any("3. Action Plan" in t for t in paragraphs_text)
    assert any("Rent is $1,850 due on the 1st." in t for t in paragraphs_text)
