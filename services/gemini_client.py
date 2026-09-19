"""Gemini API client service for LegalLens.

Provides robust multi-model fallback chains, classified error handling,
output validation, thread-safe rate-limiting, circuit breaking, caching,
and structured call logging.
"""

from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import random
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from google import genai
from google.genai import types

from services.cache import (
    compute_cache_key,
    get_cached_result,
    get_fallback_result,
    save_cached_result,
)

# Step 1: Base directory setup and environment variable loading
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Step 2: Configure logging with RotatingFileHandler (max 1 MB, 3 backups)
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOGS_DIR / "calls.log"

logger = logging.getLogger("legallens.gemini")
logger.setLevel(logging.INFO)
# Avoid duplicate handlers if re-imported
if not logger.handlers:
    handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

# Step 3: Thread-safe locks and state tracking
_rate_limit_lock = threading.Lock()
_last_call_time = 0.0

_circuit_lock = threading.Lock()
# Structure: {model_name: {"consecutive_failures": int, "skip_until": float}}
_circuit_breaker_state: Dict[str, Dict[str, Any]] = {}

_call_info_lock = threading.Lock()
_last_call_info: Dict[str, Any] = {
    "model_used": "",
    "source": "live",
    "attempts": 0,
    "fell_back": False,
    "seconds": 0.0,
}


def get_last_call_info() -> Dict[str, Any]:
    """Return metrics and provenance about the most recent call."""
    with _call_info_lock:
        return dict(_last_call_info)


def _set_last_call_info(
    model_used: str,
    source: str,
    attempts: int,
    fell_back: bool,
    seconds: float,
) -> None:
    """Safely update the last call information dict."""
    with _call_info_lock:
        _last_call_info["model_used"] = model_used
        _last_call_info["source"] = source
        _last_call_info["attempts"] = attempts
        _last_call_info["fell_back"] = fell_back
        _last_call_info["seconds"] = round(seconds, 3)


def _log_attempt(model: str, task: str, outcome: str, seconds: float) -> None:
    """Write an attempt record to logs/calls.log.

    Never logs document text or API keys.
    """
    ts = datetime.now(timezone.utc).isoformat()
    log_line = f"{ts} | {model} | {task} | {outcome} | {seconds:.2f}s"
    logger.info(log_line)


# Step 4: Model chain resolution
DEFAULT_CHAIN_HEAVY = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]

DEFAULT_CHAIN_LIGHT = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-flash-lite-latest",
]


def parse_model_chain(raw: Optional[str]) -> List[str]:
    """Parse comma-separated model string into unique, stripped list preserving order."""
    if not raw:
        return []
    models: List[str] = []
    for item in raw.split(","):
        cleaned = item.strip()
        if cleaned and cleaned not in models:
            models.append(cleaned)
    return models


def get_model_chain(task: str = "light") -> List[str]:
    """Resolve model fallback chain for light or heavy tasks."""
    env_var = "GEMINI_MODEL_CHAIN_HEAVY" if task == "heavy" else "GEMINI_MODEL_CHAIN_LIGHT"
    chain = parse_model_chain(os.environ.get(env_var))
    if chain:
        return chain

    # Fallback to single legacy GEMINI_MODEL if defined
    legacy = os.environ.get("GEMINI_MODEL")
    if legacy and legacy.strip():
        return [legacy.strip()]

    return list(DEFAULT_CHAIN_HEAVY if task == "heavy" else DEFAULT_CHAIN_LIGHT)


def get_model_name() -> str:
    """Get the primary configured Gemini model name, defaulting to gemini-3.6-flash."""
    return os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def get_client() -> genai.Client:
    """Initialize and return a google-genai Client using the GEMINI_API_KEY.

    Returns:
        genai.Client: An initialized Gemini client.

    Raises:
        ValueError: If GEMINI_API_KEY is not set in the environment or .env file.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
        root_env = BASE_DIR.parent / ".env"
        if root_env.exists():
            load_dotenv(dotenv_path=root_env, override=True)
        load_dotenv(override=True)
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please create a .env file with your "
            "Gemini API key (see .env.example) or export GEMINI_API_KEY."
        )

    return genai.Client(api_key=api_key)


# Step 5: Rate limiting and Circuit Breaker logic
def _apply_rate_limit() -> None:
    """Enforce minimum interval between API calls in a thread-safe manner."""
    global _last_call_time
    try:
        min_interval = float(os.environ.get("GEMINI_MIN_INTERVAL_SECONDS", "1.0"))
    except ValueError:
        min_interval = 1.0

    with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_call_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        _last_call_time = time.time()


def _is_model_available(model: str) -> bool:
    """Check if a model is currently allowed by the circuit breaker."""
    with _circuit_lock:
        info = _circuit_breaker_state.get(model)
        if not info:
            return True
        skip_until = info.get("skip_until", 0.0)
        return time.time() >= skip_until


def _record_model_success(model: str) -> None:
    """Reset the failure count for a model on success."""
    with _circuit_lock:
        _circuit_breaker_state[model] = {"consecutive_failures": 0, "skip_until": 0.0}


def _record_model_failure(model: str, is_severe: bool) -> None:
    """Record a failure for circuit breaker tracking (429, 503, timeout)."""
    if not is_severe:
        return
    with _circuit_lock:
        current = _circuit_breaker_state.get(model, {"consecutive_failures": 0, "skip_until": 0.0})
        fails = current["consecutive_failures"] + 1
        skip_until = current["skip_until"]
        if fails >= 2:
            skip_until = time.time() + 60.0  # Skip for 60 seconds
        _circuit_breaker_state[model] = {
            "consecutive_failures": fails,
            "skip_until": skip_until,
        }


# Step 6: Error classification helpers
def extract_error_code(exc: Exception) -> Optional[int]:
    """Extract HTTP status code from exception attribute or message string."""
    for attr in ("code", "status_code", "http_status"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
        if isinstance(val, str) and val.isdigit():
            return int(val)

    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status

    match = re.search(r"\b(400|401|403|404|429|500|502|503|504)\b", str(exc))
    if match:
        return int(match.group(1))

    return None


def extract_retry_delay(exc: Exception) -> Optional[float]:
    """Extract retry delay in seconds if specified in error message or headers."""
    msg = str(exc)
    match = re.search(r"retry\s*(?:after|in)\s*(\d+(?:\.\d+)?)\s*s", msg, re.IGNORECASE)
    if match:
        delay = float(match.group(1))
        if delay < 10.0:
            return delay

    response = getattr(exc, "response", None)
    if response and hasattr(response, "headers"):
        header = response.headers.get("retry-after")
        if header and header.isdigit():
            delay = float(header)
            if delay < 10.0:
                return delay

    return None


def is_retryable_transient_error(code: Optional[int], exc: Exception) -> bool:
    """Check if error is a transient network/server error eligible for retry."""
    if code in (429, 500, 502, 503, 504):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    msg = str(exc).lower()
    return any(k in msg for k in ("timeout", "timed out", "connection", "connect", "resource_exhausted"))


# Step 7: Core Generation Engine
def _build_content_config(
    system_instruction: Optional[str],
    response_mime_type: Optional[str] = None,
    response_schema: Optional[Any] = None,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    thinking_level: Optional[Any] = None,
    timeout_seconds: float = 35.0,
) -> types.GenerateContentConfig:
    """Construct GenerateContentConfig with timeout, retry options, and optional thinking."""
    http_opts = types.HttpOptions(
        timeout=int(timeout_seconds * 1000),
        retry_options=types.HttpRetryOptions(attempts=1),
    )

    thinking_cfg = None
    if thinking_level is not None:
        try:
            thinking_cfg = types.ThinkingConfig(thinking_level=thinking_level)
        except Exception:
            thinking_cfg = None

    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        thinking_config=thinking_cfg,
        http_options=http_opts,
    )


def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    max_retries: int = 2,
    client: Optional[genai.Client] = None,
    task: str = "light",
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    thinking_level: Optional[Any] = None,
) -> str:
    """Generate plain text with multi-model fallback, caching, and robust error handling.

    Args:
        prompt: The user prompt or document text.
        system_instruction: Optional system guidance.
        max_retries: Retry attempts for transient errors per model (default: 2).
        client: Optional pre-configured client (useful for testing).
        task: 'light' or 'heavy' (determines model chain).
        temperature: Sampling temperature.
        max_output_tokens: Token cap.
        thinking_level: Optional model thinking level.

    Returns:
        Generated text string.

    Raises:
        RuntimeError: If all models fail.
    """
    start_total = time.time()
    cache_key = compute_cache_key(prompt, system_instruction, None, task)

    # 1. Check cache before calling API
    cached = get_cached_result(cache_key)
    if isinstance(cached, str):
        _set_last_call_info("cache", "cache", 0, False, time.time() - start_total)
        return cached

    active_client = client or get_client()

    try:
        timeout_sec = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "35"))
    except ValueError:
        timeout_sec = 35.0

    models = get_model_chain(task)
    # If all models in circuit breaker are skipped, try them anyway
    available_models = [m for m in models if _is_model_available(m)]
    candidate_models = available_models if available_models else models

    total_attempts = 0
    model_errors: List[str] = []

    for model_index, model in enumerate(candidate_models):
        current_thinking = thinking_level
        attempt = 0

        while attempt <= max_retries:
            total_attempts += 1
            attempt_start = time.time()
            _apply_rate_limit()

            config = _build_content_config(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                thinking_level=current_thinking,
                timeout_seconds=timeout_sec,
            )

            try:
                response = active_client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                duration = time.time() - attempt_start

                # Output validation
                text = getattr(response, "text", None)
                if not text or not text.strip():
                    raise ValueError(f"Empty or blocked response from model '{model}'")

                # Success: record metrics, update cache, and return
                _record_model_success(model)
                _log_attempt(model, task, "ok", duration)
                save_cached_result(cache_key, text)
                fell_back = model_index > 0
                _set_last_call_info(model, "live", total_attempts, fell_back, time.time() - start_total)
                return text

            except Exception as exc:
                duration = time.time() - attempt_start
                code = extract_error_code(exc)
                outcome_str = f"err:{code}" if code else f"err:{exc.__class__.__name__}"
                _log_attempt(model, task, outcome_str, duration)

                # 401 / 403: Stop immediately
                if code in (401, 403):
                    raise RuntimeError("Gemini API request failed: API key invalid or unauthorized.") from exc

                # 404: Move to next model immediately with no retry
                if code == 404:
                    model_errors.append(f"{model}: 404 Not Found")
                    break

                # 400 with "thinking": Retry once without thinking
                if code == 400 and "thinking" in str(exc).lower() and current_thinking is not None:
                    current_thinking = None
                    attempt += 1
                    continue

                # Other 400 errors: Stop immediately
                if code == 400:
                    clean_msg = " ".join(str(exc).split())[:120]
                    raise RuntimeError(f"Bad request error from {model}: {clean_msg}") from exc

                # Transient errors (429, 500, 502, 503, 504, timeout, connection)
                if is_retryable_transient_error(code, exc):
                    is_severe = code in (429, 503) or isinstance(exc, (TimeoutError, ConnectionError))
                    _record_model_failure(model, is_severe=is_severe)
                    if attempt < max_retries:
                        # Exponential backoff: 1s, 2s + 0-0.5s jitter
                        backoff = (2 ** attempt) + random.uniform(0, 0.5)
                        retry_delay = extract_retry_delay(exc)
                        delay = retry_delay if (retry_delay is not None and retry_delay < 10.0) else backoff
                        time.sleep(delay)
                        attempt += 1
                        continue
                    else:
                        model_errors.append(f"{model}: {exc.__class__.__name__} ({code or 'network'})")
                        break


                # Unhandled error: record and advance to next model
                model_errors.append(f"{model}: {str(exc)[:80]}")
                break

    # All models failed: attempt fallback to cache or demo_data
    fallback, source = get_fallback_result(cache_key)
    if isinstance(fallback, str):
        _set_last_call_info("fallback", source or "demo", total_attempts, True, time.time() - start_total)
        return fallback

    raise RuntimeError(
        f"Failed to generate text after {max_retries} retries: {'; '.join(model_errors)}"
    )


def generate_json(
    prompt: str,
    schema: Any,
    system_instruction: Optional[str] = None,
    max_retries: int = 2,
    client: Optional[genai.Client] = None,
    task: str = "light",
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    thinking_level: Optional[Any] = None,
) -> Dict[str, Any]:
    """Generate structured output conforming to schema with fallback and validation.

    Args:
        prompt: The user prompt or document text.
        schema: Expected JSON schema dict.
        system_instruction: Optional system instruction.
        max_retries: Retry attempts for transient errors per model (default: 2).
        client: Optional pre-configured client.
        task: 'light' or 'heavy'.
        temperature: Sampling temperature.
        max_output_tokens: Token cap.
        thinking_level: Optional thinking level.

    Returns:
        Parsed dictionary matching the schema.

    Raises:
        RuntimeError: If all models fail.
    """
    start_total = time.time()
    cache_key = compute_cache_key(prompt, system_instruction, schema, task)

    # 1. Check cache before calling API
    cached = get_cached_result(cache_key)
    if isinstance(cached, dict):
        _set_last_call_info("cache", "cache", 0, False, time.time() - start_total)
        return cached

    active_client = client or get_client()

    try:
        timeout_sec = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "35"))
    except ValueError:
        timeout_sec = 35.0

    models = get_model_chain(task)
    available_models = [m for m in models if _is_model_available(m)]
    candidate_models = available_models if available_models else models

    total_attempts = 0
    model_errors: List[str] = []

    # Required fields from schema
    required_fields: List[str] = []
    if isinstance(schema, dict) and "required" in schema:
        required_fields = list(schema.get("required", []))

    for model_index, model in enumerate(candidate_models):
        current_thinking = thinking_level
        current_temp = temperature
        current_prompt = prompt
        attempt = 0
        json_correction_retried = False

        while attempt <= max_retries:
            total_attempts += 1
            attempt_start = time.time()
            _apply_rate_limit()

            config = _build_content_config(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=current_temp,
                max_output_tokens=max_output_tokens,
                thinking_level=current_thinking,
                timeout_seconds=timeout_sec,
            )

            try:
                response = active_client.models.generate_content(
                    model=model,
                    contents=current_prompt,
                    config=config,
                )
                duration = time.time() - attempt_start

                text = getattr(response, "text", None)
                if not text or not text.strip():
                    raise ValueError(f"Empty response from model '{model}'")

                # Strip markdown json code fences if present
                clean_text = text.strip()
                if clean_text.startswith("```"):
                    clean_text = re.sub(r"^```(?:json)?\n?", "", clean_text, flags=re.IGNORECASE)
                    clean_text = re.sub(r"\n?```$", "", clean_text)
                    clean_text = clean_text.strip()

                parsed = json.loads(clean_text)

                if not isinstance(parsed, dict):
                    raise ValueError(f"Parsed JSON is not a dictionary: {type(parsed)}")

                # Validate required schema fields
                missing_keys = [k for k in required_fields if k not in parsed]
                if missing_keys:
                    raise ValueError(f"Missing required fields {missing_keys} in JSON response")

                # Success
                _record_model_success(model)
                _log_attempt(model, task, "ok", duration)
                save_cached_result(cache_key, parsed)
                fell_back = model_index > 0
                _set_last_call_info(model, "live", total_attempts, fell_back, time.time() - start_total)
                return parsed

            except (json.JSONDecodeError, ValueError) as parse_err:
                duration = time.time() - attempt_start
                _log_attempt(model, task, "err:json_parse", duration)

                # Retry ONCE with temperature 0 and extra instruction
                if not json_correction_retried:
                    json_correction_retried = True
                    current_temp = 0.0
                    current_prompt = f"{prompt}\nReturn only valid JSON matching the schema."
                    attempt += 1
                    continue
                else:
                    model_errors.append(f"{model}: JSON parse failure ({parse_err})")
                    break

            except Exception as exc:
                duration = time.time() - attempt_start
                code = extract_error_code(exc)
                outcome_str = f"err:{code}" if code else f"err:{exc.__class__.__name__}"
                _log_attempt(model, task, outcome_str, duration)

                # 401 / 403: Stop immediately
                if code in (401, 403):
                    raise RuntimeError("Gemini API request failed: API key invalid or unauthorized.") from exc

                # 404: Move to next model immediately
                if code == 404:
                    model_errors.append(f"{model}: 404 Not Found")
                    break

                # 400 with "thinking": Retry once without thinking
                if code == 400 and "thinking" in str(exc).lower() and current_thinking is not None:
                    current_thinking = None
                    attempt += 1
                    continue

                # Other 400: Stop immediately
                if code == 400:
                    clean_msg = " ".join(str(exc).split())[:120]
                    raise RuntimeError(f"Bad request error from {model}: {clean_msg}") from exc

                # Transient errors (429, 500, 502, 503, 504, timeout, connection)
                if is_retryable_transient_error(code, exc):
                    is_severe = code in (429, 503) or isinstance(exc, (TimeoutError, ConnectionError))
                    _record_model_failure(model, is_severe=is_severe)
                    if attempt < max_retries:
                        backoff = (2 ** attempt) + random.uniform(0, 0.5)
                        retry_delay = extract_retry_delay(exc)
                        delay = retry_delay if (retry_delay is not None and retry_delay < 10.0) else backoff
                        time.sleep(delay)
                        attempt += 1
                        continue
                    else:
                        model_errors.append(f"{model}: {exc.__class__.__name__} ({code or 'network'})")
                        break


                model_errors.append(f"{model}: {str(exc)[:80]}")
                break

    # All models failed: check fallback in cache or demo_data
    fallback, source = get_fallback_result(cache_key)
    if isinstance(fallback, dict):
        _set_last_call_info("fallback", source or "demo", total_attempts, True, time.time() - start_total)
        return fallback

    raise RuntimeError(
        f"Failed to generate valid structured JSON after {max_retries} retries: {'; '.join(model_errors)}"
    )
