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


def install_pre_v5_historical_g1_transaction(layout: Any, transaction: Any) -> Any:
    """Install one frozen pre-v5 G1 Decision as historical test evidence.

    Production commit paths must enforce the current framing preflight.  A few
    frozen Phase 2 regression chains nevertheless need to reconstruct bytes
    that were admissible before that policy existed.  This deliberately narrow
    test-only installer validates the transaction with historical replay
    semantics, installs its immutable bytes, and advances the test store head.
    It accepts no route operation and no non-G1 Decision.
    """

    from econ_theorist.codec import (
        canonical_json_bytes,
        transaction_bytes,
        transaction_digest,
    )
    from econ_theorist.models import RecordDecisionOp, SupersedeDecisionOp
    from econ_theorist.runtime.lock import ExclusiveFileLock
    from econ_theorist.runtime.objects import HeadStore, ObjectStore
    from econ_theorist.runtime.replay import replay, validate_candidate

    decision_operations = tuple(
        operation
        for operation in transaction.operations
        if isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp))
    )
    if (
        transaction.origin != "human_decision"
        or len(decision_operations) != len(transaction.operations)
        or not decision_operations
        or any(
            operation.decision.decision_kind != "G1_question_benchmark"
            for operation in decision_operations
        )
    ):
        raise AssertionError(
            "historical installer accepts only pre-v5 G1 Decision transactions"
        )

    layout.ensure()
    heads = HeadStore(layout)
    store = ObjectStore(layout)
    with ExclusiveFileLock(layout.commit_lock):
        head_before = heads.read()
        if head_before is None or transaction.base_revision != head_before:
            raise AssertionError(
                "historical G1 transaction must extend the exact current test head"
            )
        base = replay(layout)
        projected = validate_candidate(base, transaction)
        digest = transaction_digest(transaction)
        store.install_bytes("transactions", digest, transaction_bytes(transaction))
        heads.replace(head_before, digest)

    replayed = replay(layout)
    if canonical_json_bytes(replayed) != canonical_json_bytes(projected):
        raise AssertionError("historical G1 installation does not replay exactly")
    return replayed
