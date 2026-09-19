"""Tests for the qa_service module."""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from services.qa_service import ask_question


def test_ask_question_success():
    """Test ask_question with a mocked successful response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "answer": "Rent is $1,850 per month, due on the first day of each calendar month.",
        "supporting_quotes": ["Tenant agrees to pay monthly rent in the amount of $1,850.00 USD"],
        "confidence": "High",
        "needs_lawyer": False,
    })
    mock_client.models.generate_content.return_value = mock_response

    result = ask_question(
        document_text="Rent is $1,850.00 USD due on the 1st.",
        question="How much is rent?",
        client=mock_client,
    )

    assert result["answer"] == "Rent is $1,850 per month, due on the first day of each calendar month."
    assert len(result["supporting_quotes"]) == 1
    assert result["confidence"] == "High"
    assert result["needs_lawyer"] is False


def test_ask_question_not_in_document():
    """Test ask_question when document does not cover the topic."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "answer": "The document doesn't cover this. Ask a lawyer whether the landlord must provide free Wi-Fi under municipal bylaws.",
        "supporting_quotes": [],
        "confidence": "Low",
        "needs_lawyer": True,
    })
    mock_client.models.generate_content.return_value = mock_response

    result = ask_question(
        document_text="Rent is $1,850.00 USD due on the 1st.",
        question="Does the landlord provide free Wi-Fi?",
        client=mock_client,
    )

    assert "The document doesn't cover this" in result["answer"]
    assert result["needs_lawyer"] is True
    assert result["supporting_quotes"] == []


def test_ask_question_trims_history_to_last_six():
    """Test that only the last 6 messages of chat history are included in the prompt."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "answer": "Test answer",
        "supporting_quotes": [],
        "confidence": "Medium",
        "needs_lawyer": False,
    })
    mock_client.models.generate_content.return_value = mock_response

    # Create 10 historical messages
    ten_messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message number {i}"}
        for i in range(1, 11)
    ]

    ask_question(
        document_text="Sample document text",
        question="Current question",
        chat_history=ten_messages,
        client=mock_client,
    )

    # Check the call arguments passed to generate_content
    call_args = mock_client.models.generate_content.call_args
    prompt_sent = call_args.kwargs.get("contents") or call_args[1].get("contents")

    # Messages 1 to 4 should NOT be in the prompt (only last 6: messages 5 to 10)
    assert "Message number 1\n" not in prompt_sent
    assert "Message number 2\n" not in prompt_sent
    assert "Message number 3\n" not in prompt_sent
    assert "Message number 4\n" not in prompt_sent

    # Messages 5 to 10 SHOULD be present
    assert "Message number 5" in prompt_sent
    assert "Message number 10" in prompt_sent


def test_ask_question_empty_inputs():
    """Test that empty document or question raises ValueError."""
    with pytest.raises(ValueError, match="Cannot answer questions without document text"):
        ask_question("", "What is the rent?")

    with pytest.raises(ValueError, match="Question cannot be empty"):
        ask_question("Document text here", "   ")
