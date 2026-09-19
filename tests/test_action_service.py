"""Tests for the action_service module."""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from services.action_service import generate_action_plan


def test_generate_action_plan_success():
    """Test generating an action plan with mocked Gemini client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "checklist_before_signing": [
            "Inspect condition of apartment and document existing damages.",
            "Confirm receipt of security deposit in an escrow account.",
        ],
        "obligations_and_deadlines": [
            {"what": "Pay monthly rent of $1,850", "who": "Tenant", "when": "1st of each month"},
            {"what": "Return security deposit", "who": "Landlord", "when": "Within 30 days of surrender"},
        ],
        "questions_for_a_lawyer": [
            "Is the $75 late fee permitted under local municipal caps?",
            "Can the landlord deduct from deposit without an itemized list?",
            "What constitutes acceptable proof of damage under Illinois law?",
            "Can the landlord increase rent during a month-to-month holdover?",
            "What are the statutory requirements for heating maintenance?",
            "Does the pet policy non-refundable fee violate local deposit limits?",
            "Is the 5-day notice period standard for cure in this jurisdiction?",
            "What rights does the tenant have if the landlord enters without notice?",
        ],
        "possible_next_steps": [
            "Request written clarification on appliance maintenance.",
            "Take move-in photos before moving furniture.",
        ],
        "documents_to_gather": [
            "Move-in inspection checklist signed by both parties.",
            "Bank receipts for deposit and first month's rent.",
        ],
    })
    mock_client.models.generate_content.return_value = mock_response

    result = generate_action_plan("Sample contract text", client=mock_client)

    assert len(result["checklist_before_signing"]) == 2
    assert len(result["obligations_and_deadlines"]) == 2
    assert len(result["questions_for_a_lawyer"]) == 8
    assert len(result["possible_next_steps"]) == 2
    assert len(result["documents_to_gather"]) == 2
    assert mock_client.models.generate_content.call_count == 1


def test_generate_action_plan_empty_document():
    """Test that empty document raises ValueError."""
    with pytest.raises(ValueError, match="Cannot generate an action plan for an empty document"):
        generate_action_plan("")
