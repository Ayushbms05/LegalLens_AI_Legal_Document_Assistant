"""check_models.py - Test Gemini models for plain text and JSON mode capabilities."""

import json
import os
from pathlib import Path
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Step 1: Locate and load the .env file containing the GEMINI_API_KEY
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY"):
        parent_env = Path(__file__).resolve().parent.parent / ".env"
        if parent_env.exists():
            load_dotenv(dotenv_path=parent_env)

# Step 2: Retrieve the API key and initialize the Google GenAI client
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("ERROR: GEMINI_API_KEY is not set in .env. Please add it first.")
    raise SystemExit(1)

# Initialize the client without printing or exposing the API key
client = genai.Client(api_key=api_key)

# Step 3: Define the list of candidate models to test
MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]

# Step 4: Define a simple JSON schema for the structured JSON mode test
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
    },
    "required": ["status"],
}

print("=" * 70)
print("Testing Gemini Models: Text and Structured JSON Mode")
print("=" * 70)

# Step 5: Iterate through each model and run both text and JSON tests
for model_name in MODELS:
    # -------------------------------------------------------------
    # Test 1: Plain text generation
    # -------------------------------------------------------------
    # Measure execution time for the plain text call
    start_time = time.time()
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Reply with the single word OK",
        )
        elapsed = time.time() - start_time
        text_result = (response.text or "").strip()
        print(f"{model_name} | text | OK | {elapsed:.1f}s")
    except Exception as exc:
        elapsed = time.time() - start_time
        # Clean and truncate error message to first 120 characters
        clean_error = " ".join(str(exc).split())[:120]
        print(f"{model_name} | text | FAILED | {clean_error}")

    # Step 6: Wait 3 seconds between calls to prevent rate limits
    time.sleep(3)

    # -------------------------------------------------------------
    # Test 2: Structured JSON mode generation
    # -------------------------------------------------------------
    # Measure execution time for the JSON mode call
    start_time = time.time()
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JSON_SCHEMA,
        )
        response = client.models.generate_content(
            model=model_name,
            contents='Return a JSON object with {"status": "ok"}',
            config=config,
        )
        elapsed = time.time() - start_time
        # Parse the JSON output to verify structure
        parsed = json.loads(response.text)
        print(f"{model_name} | json | OK | {elapsed:.1f}s")
    except Exception as exc:
        elapsed = time.time() - start_time
        # Clean and truncate error message to first 120 characters
        clean_error = " ".join(str(exc).split())[:120]
        print(f"{model_name} | json | FAILED | {clean_error}")

    # Step 7: Wait 3 seconds before testing the next model
    time.sleep(3)

print("=" * 70)
print("Model check complete.")
