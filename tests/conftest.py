"""
conftest.py — Shared pytest fixtures and path setup for phnv-skills test suite.

Scripts live in skills/fact-check-stack/scripts/ relative to the project root.
We add that directory to sys.path so tests can import them directly.
"""

import sys
from pathlib import Path

# Project root is one level up from this file (tests/ → project root)
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "fact-check-stack" / "scripts"

# Make scripts importable without install
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
