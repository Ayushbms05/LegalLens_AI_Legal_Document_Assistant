"""Smoke test to verify that app.py can be imported without errors."""

import sys
from pathlib import Path

# Ensure the legallens root directory is on sys.path
LEGALLENS_DIR = Path(__file__).resolve().parent.parent
if str(LEGALLENS_DIR) not in sys.path:
    sys.path.insert(0, str(LEGALLENS_DIR))


def test_import_app():
    """Verify that the app module can be imported successfully."""
    import app

    assert hasattr(app, "main")
    assert callable(app.main)
