"""Tests for the legal_checker utility."""

from pathlib import Path
import sys

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from utils.legal_checker import is_likely_legal_document


def test_is_likely_legal_document_positive():
    """Test that text with legal terms is correctly identified as a legal document."""
    legal_text = (
        "This Agreement is entered into between the parties. "
        "The Tenant shall pay rent, and liability is governed by the laws of Illinois. "
        "Termination requires 30 days notice."
    )
    assert is_likely_legal_document(legal_text) is True


def test_is_likely_legal_document_negative():
    """Test that everyday non-legal text is flagged as unlikely to be a legal document."""
    recipe_text = (
        "Preheat the oven to 350 degrees. Mix flour, sugar, and butter in a large bowl. "
        "Bake for 25 minutes until golden brown."
    )
    assert is_likely_legal_document(recipe_text) is False


def test_is_likely_legal_document_empty():
    """Test that empty or blank text returns False."""
    assert is_likely_legal_document("") is False
    assert is_likely_legal_document("   \n\t  ") is False
