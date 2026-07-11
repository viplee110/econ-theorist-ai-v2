"""Small, stdlib-only helpers shared by Phase 1 contract tests.

The project uses a ``src`` layout but the contract suite must also run directly
from a source checkout with ``python -m unittest``.  Import path setup therefore
lives here rather than in an external test runner configuration.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def sha256_bytes(data: bytes) -> str:
    """Return the test oracle for a SHA-256 content address."""

    return hashlib.sha256(data).hexdigest()


def assert_valid_sha256(test_case: Any, value: str) -> None:
    """Assert that *value* is exactly one lowercase SHA-256 digest."""

    test_case.assertIsInstance(value, str)
    test_case.assertIsNotNone(SHA256_PATTERN.fullmatch(value))


def load_json_bytes(data: bytes) -> Any:
    """Decode canonical JSON without accepting a BOM or non-UTF-8 bytes."""

    text = data.decode("utf-8")
    if text.startswith("\ufeff"):
        raise AssertionError("canonical JSON must not contain a UTF-8 BOM")
    return json.loads(text)


def assert_generated_view(test_case: Any, text: str, source_head: str) -> None:
    """Apply the minimum nonauthority oracle to a generated status view."""

    test_case.assertIn("GENERATED", text)
    test_case.assertIn("NONCANONICAL", text)
    test_case.assertIn("source_head", text)
    test_case.assertIn(source_head, text)
