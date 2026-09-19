"""Cache and offline fallback service for LegalLens.

Provides file-based caching in .cache/ and offline fallback to demo_data/.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

# Define base paths relative to the legallens package directory
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".cache"
DEMO_DIR = BASE_DIR / "demo_data"


def compute_cache_key(
    prompt: str,
    system_instruction: Optional[str] = None,
    schema: Optional[Any] = None,
    task: str = "light",
) -> str:
    """Compute SHA-256 cache key from request parameters.

    Excludes model name and API key to allow model-agnostic caching.

    Args:
        prompt: The input prompt string.
        system_instruction: Optional system instruction.
        schema: Optional JSON schema.
        task: The task type ('light' or 'heavy').

    Returns:
        Hexadecimal SHA-256 hash string.
    """
    # Normalize schema into a deterministic JSON string
    schema_str = ""
    if schema is not None:
        try:
            schema_str = json.dumps(schema, sort_keys=True)
        except Exception:
            schema_str = str(schema)

    raw_key = (
        f"sys:{system_instruction or ''}|"
        f"prompt:{prompt}|"
        f"schema:{schema_str}|"
        f"task:{task}"
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_cached_result(cache_key: str) -> Optional[Union[str, Dict[str, Any]]]:
    """Retrieve a validated result from .cache/ by key.

    Ignores corrupt or unreadable cache files without crashing.

    Args:
        cache_key: SHA-256 hash key.

    Returns:
        Cached text or dict, or None if not found or corrupt.
    """
    # When running under pytest and CACHE_DIR has not been explicitly redirected,
    # avoid reading from the workspace .cache directory so unit tests execute cleanly.
    if "PYTEST_CURRENT_TEST" in os.environ and CACHE_DIR == BASE_DIR / ".cache":
        return None

    file_path = CACHE_DIR / f"{cache_key}.json"
    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Returns the actual stored payload
            return data.get("payload")
    except Exception:
        # Corrupt or unreadable cache file; ignore safely
        return None


def save_cached_result(cache_key: str, payload: Union[str, Dict[str, Any]]) -> None:
    """Save a validated result into .cache/.

    Args:
        cache_key: SHA-256 hash key.
        payload: Validated text or dictionary.
    """
    # When running under pytest and CACHE_DIR has not been explicitly redirected,
    # avoid writing to the workspace .cache directory so unit tests don't pollute cache.
    if "PYTEST_CURRENT_TEST" in os.environ and CACHE_DIR == BASE_DIR / ".cache":
        return

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = CACHE_DIR / f"{cache_key}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"payload": payload}, f, indent=2)
    except Exception:
        # Never crash on cache write failure
        pass


def get_fallback_result(
    cache_key: str,
) -> Tuple[Optional[Union[str, Dict[str, Any]]], Optional[str]]:
    """Look for a fallback result first in .cache/, then in demo_data/.

    Args:
        cache_key: SHA-256 hash key.

    Returns:
        Tuple of (payload, source) where source is 'cache', 'demo', or None.
    """
    # 1. First check .cache/
    cached = get_cached_result(cache_key)
    if cached is not None:
        return cached, "cache"

    # 2. Then check demo_data/
    demo_path = DEMO_DIR / f"{cache_key}.json"
    if demo_path.exists():
        try:
            with open(demo_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                payload = data.get("payload", data)
                return payload, "demo"
        except Exception:
            # Corrupt demo file; ignore safely
            pass

    return None, None
