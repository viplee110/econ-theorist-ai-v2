"""Prepare one candidate, synchronize, then race for the canonical head."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from tests.helpers import SOURCE_ROOT  # noqa: F401

from econ_theorist.models import Transaction
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import commit_prepared, preflight_candidate


def main() -> int:
    if len(sys.argv) != 6:
        return 64
    root, candidate_path, ready_path, go_path, result_path = map(Path, sys.argv[1:])
    transaction = Transaction.model_validate_json(
        candidate_path.read_bytes(), strict=True
    )
    prepared = preflight_candidate(StoreLayout.at(root), transaction)
    ready_path.write_text("ready\n", encoding="ascii")
    deadline = time.monotonic() + 20
    while not go_path.exists():
        if time.monotonic() >= deadline:
            return 65
        time.sleep(0.01)
    result = commit_prepared(StoreLayout.at(root), prepared, lock_timeout=10)
    result_path.write_text(
        json.dumps(
            {
                "status": result.status,
                "transaction_digest": result.transaction_digest,
                "head_after": result.head_after,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
