"""Tests for services/cache.py."""

from pathlib import Path
import sys
import pytest

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))

from services.cache import (
    compute_cache_key,
    get_cached_result,
    get_fallback_result,
    save_cached_result,
)


def test_compute_cache_key_deterministic():
    """Verify that compute_cache_key is deterministic and excludes model/key."""
    k1 = compute_cache_key("prompt 1", "instruction", {"type": "object"}, "light")
    k2 = compute_cache_key("prompt 1", "instruction", {"type": "object"}, "light")
    assert k1 == k2

    # Different prompt produces different key
    k3 = compute_cache_key("prompt 2", "instruction", {"type": "object"}, "light")
    assert k1 != k3


def test_save_and_get_cached_result(tmp_path, monkeypatch):
    """Test writing to and reading from cache."""
    monkeypatch.setattr("services.cache.CACHE_DIR", tmp_path / ".cache")

    key = "test_key_123"
    payload = {"status": "ok", "items": [1, 2, 3]}

    # Initially empty
    assert get_cached_result(key) is None

    # Save and retrieve
    save_cached_result(key, payload)
    retrieved = get_cached_result(key)
    assert retrieved == payload


def test_corrupt_cache_file_ignored(tmp_path, monkeypatch):
    """Test that corrupt or unreadable cache file is ignored without error."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("services.cache.CACHE_DIR", cache_dir)

    corrupt_file = cache_dir / "corrupt_key.json"
    corrupt_file.write_text("NOT A VALID JSON FILE", encoding="utf-8")

    assert get_cached_result("corrupt_key") is None


def test_get_fallback_result_demo(tmp_path, monkeypatch):
    """Test fallback to demo_data when not in cache."""
    cache_dir = tmp_path / ".cache"
    demo_dir = tmp_path / "demo_data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    demo_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("services.cache.CACHE_DIR", cache_dir)
    monkeypatch.setattr("services.cache.DEMO_DIR", demo_dir)

    key = "demo_key_456"
    demo_payload = {"source": "demo_data"}
    (demo_dir / f"{key}.json").write_text('{"payload": {"source": "demo_data"}}', encoding="utf-8")

    payload, source = get_fallback_result(key)
    assert payload == demo_payload
    assert source == "demo"
