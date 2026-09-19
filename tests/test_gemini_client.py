"""Tests for the Gemini client service, mocking API calls."""

import json
import os
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import pytest

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from services.gemini_client import (
    _circuit_breaker_state,
    generate_json,
    generate_text,
    get_client,
    get_last_call_info,
    get_model_chain,
    get_model_name,
)


class FakeAPIError(Exception):
    """Mock API error carrying HTTP status codes."""

    def __init__(self, message: str, code: int):
        super().__init__(message)
        self.code = code
        self.status_code = code


@pytest.fixture(autouse=True)
def reset_state_and_cache(tmp_path, monkeypatch):
    """Reset circuit breaker and redirect cache/logs to temporary directory."""
    _circuit_breaker_state.clear()
    monkeypatch.setattr("services.gemini_client.get_cached_result", lambda k: None)
    monkeypatch.setattr("services.gemini_client.save_cached_result", lambda k, v: None)
    monkeypatch.setattr("services.gemini_client.get_fallback_result", lambda k: (None, None))
    # Ensure min interval doesn't slow tests down
    monkeypatch.setenv("GEMINI_MIN_INTERVAL_SECONDS", "0.0")


def test_get_model_name_default(monkeypatch):
    """Test default model name when GEMINI_MODEL is not set."""
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert get_model_name() == "gemini-3.6-flash"


def test_get_model_name_configured(monkeypatch):
    """Test custom model name via GEMINI_MODEL."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-pro")
    assert get_model_name() == "gemini-1.5-pro"


def test_get_client_missing_key(monkeypatch):
    """Test that get_client raises ValueError when GEMINI_API_KEY is missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("services.gemini_client.load_dotenv", lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
        get_client()


def test_get_client_with_key(monkeypatch):
    """Test that get_client returns a genai.Client when key is present."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake_test_key_123")
    client = get_client()
    assert client is not None


def test_first_model_succeeds():
    """Test that if the first model in the chain succeeds, subsequent models are not called."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Model 1 text"
    mock_client.models.generate_content.return_value = mock_resp

    with patch("time.sleep"):
        res = generate_text("Hello", client=mock_client, task="light")

    assert res == "Model 1 text"
    # Should only call once for the first model
    assert mock_client.models.generate_content.call_count == 1
    call_info = get_last_call_info()
    assert call_info["source"] == "live"
    assert call_info["fell_back"] is False


def test_404_goes_straight_to_next_model_no_sleep():
    """Test that a 404 error moves immediately to the next model without retrying or sleeping."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Fallback model text"

    # First model raises 404, second succeeds
    mock_client.models.generate_content.side_effect = [
        FakeAPIError("models/gemini-old is not found", 404),
        mock_resp,
    ]

    with patch("time.sleep") as mock_sleep:
        res = generate_text("Hello", client=mock_client, task="light")

    assert res == "Fallback model text"
    assert mock_client.models.generate_content.call_count == 2
    # Sleep should NOT have been called for retry backoff
    assert mock_sleep.call_count == 0
    call_info = get_last_call_info()
    assert call_info["fell_back"] is True


def test_429_retries_then_falls_back():
    """Test that 429 retries same model up to max_retries then moves to next model."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Model 2 text after fallback"

    # Model 1 fails with 429 3 times (1 initial + 2 retries), then Model 2 succeeds
    mock_client.models.generate_content.side_effect = [
        FakeAPIError("Rate limit exceeded", 429),
        FakeAPIError("Rate limit exceeded", 429),
        FakeAPIError("Rate limit exceeded", 429),
        mock_resp,
    ]

    with patch("time.sleep") as mock_sleep:
        res = generate_text("Hello", client=mock_client, max_retries=2, task="light")

    assert res == "Model 2 text after fallback"
    assert mock_client.models.generate_content.call_count == 4
    # Sleep should have been called twice for backoff on model 1
    assert mock_sleep.call_count == 2
    call_info = get_last_call_info()
    assert call_info["fell_back"] is True


def test_401_stops_at_once():
    """Test that 401 unauthorized stops immediately without retrying or falling back."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = FakeAPIError("API key not valid", 401)

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError, match="API key invalid or unauthorized"):
            generate_text("Hello", client=mock_client)

    # Must only call once and stop
    assert mock_client.models.generate_content.call_count == 1
    assert mock_sleep.call_count == 0


def test_invalid_json_retries_then_falls_back():
    """Test that invalid JSON triggers one retry with temperature 0, then falls back."""
    mock_client = MagicMock()
    mock_resp_bad = MagicMock()
    mock_resp_bad.text = "NOT JSON"

    mock_resp_good = MagicMock()
    mock_resp_good.text = '{"status": "ok"}'

    # Model 1 fails twice (initial + 1 retry with temp 0), then Model 2 succeeds
    mock_client.models.generate_content.side_effect = [
        mock_resp_bad,
        mock_resp_bad,
        mock_resp_good,
    ]

    schema = {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}

    with patch("time.sleep"):
        res = generate_json("Get json", schema=schema, client=mock_client)

    assert res == {"status": "ok"}
    assert mock_client.models.generate_content.call_count == 3


def test_all_models_fail_returns_friendly_error(monkeypatch):
    """Test that when all models fail, a single friendly RuntimeError is raised."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = FakeAPIError("Model retired", 404)

    # Use a small 2-model chain for testing
    monkeypatch.setenv("GEMINI_MODEL_CHAIN_LIGHT", "model-a,model-b")

    with patch("time.sleep"):
        with pytest.raises(RuntimeError, match="Failed to generate text after 2 retries: model-a: 404 Not Found; model-b: 404 Not Found"):
            generate_text("Hello", client=mock_client)

    assert mock_client.models.generate_content.call_count == 2


def test_circuit_breaker_skips_and_resets(monkeypatch):
    """Test that a model with 2 consecutive severe failures is skipped, and resets on success."""
    monkeypatch.setenv("GEMINI_MODEL_CHAIN_LIGHT", "model-flaky,model-backup")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Backup response"

    # Call 1: model-flaky fails with 429 on all retries, model-backup succeeds
    mock_client.models.generate_content.side_effect = [
        FakeAPIError("429", 429),
        FakeAPIError("429", 429),
        FakeAPIError("429", 429),
        mock_resp,
    ]

    with patch("time.sleep"):
        res1 = generate_text("Call 1", client=mock_client, max_retries=2)
    assert res1 == "Backup response"

    # model-flaky should now be in circuit breaker skipped state
    assert _circuit_breaker_state["model-flaky"]["consecutive_failures"] >= 2
    assert _circuit_breaker_state["model-flaky"]["skip_until"] > 0

    # Call 2: model-flaky should be SKIPPED directly, calling model-backup immediately
    mock_resp_2 = MagicMock()
    mock_resp_2.text = "Backup response 2"
    mock_client.models.generate_content.side_effect = [mock_resp_2]

    with patch("time.sleep"):
        res2 = generate_text("Call 2", client=mock_client)
    assert res2 == "Backup response 2"

    # Verify model-flaky was skipped (generate_content only called once for model-backup)
    assert mock_client.models.generate_content.call_count == 5


def test_cache_hit_avoids_api_call(monkeypatch):
    """Test that a cache hit returns immediately without calling the API client."""
    monkeypatch.setattr("services.gemini_client.get_cached_result", lambda k: "Cached output")

    mock_client = MagicMock()
    res = generate_text("Cached prompt", client=mock_client)

    assert res == "Cached output"
    assert mock_client.models.generate_content.call_count == 0
    call_info = get_last_call_info()
    assert call_info["source"] == "cache"


def test_demo_fallback_works(monkeypatch):
    """Test that demo_data fallback is used when all models fail."""
    monkeypatch.setenv("GEMINI_MODEL_CHAIN_LIGHT", "model-fail")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = FakeAPIError("404", 404)

    monkeypatch.setattr(
        "services.gemini_client.get_fallback_result",
        lambda k: ("Fallback demo output", "demo"),
    )

    with patch("time.sleep"):
        res = generate_text("Prompt requiring fallback", client=mock_client)

    assert res == "Fallback demo output"
    call_info = get_last_call_info()
    assert call_info["source"] == "demo"
    assert call_info["fell_back"] is True


def test_api_key_and_doc_never_in_log(tmp_path, monkeypatch):
    """Verify that neither the API key nor the document text ever appear in calls.log."""
    log_file = tmp_path / "calls.log"
    import logging
    test_logger = logging.getLogger("legallens.gemini.test")
    test_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    test_logger.addHandler(handler)
    monkeypatch.setattr("services.gemini_client.logger", test_logger)

    secret_key = "SECRET_API_KEY_999"
    secret_document = "CONFIDENTIAL CONTRACT FOR SECRET PROJECT X"

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Public response"
    mock_client.models.generate_content.return_value = mock_resp

    monkeypatch.setenv("GEMINI_API_KEY", secret_key)

    with patch("time.sleep"):
        generate_text(secret_document, client=mock_client)

    handler.flush()
    log_contents = log_file.read_text(encoding="utf-8")

    assert secret_key not in log_contents
    assert secret_document not in log_contents
    assert "ok" in log_contents
