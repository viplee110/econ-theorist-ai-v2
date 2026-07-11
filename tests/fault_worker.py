"""Child-process commit worker used to exercise abrupt os._exit faults."""

from __future__ import annotations

import sys
from pathlib import Path

from tests.helpers import SOURCE_ROOT  # noqa: F401

from econ_theorist.models import Transaction
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import commit_transaction


def main() -> int:
    if len(sys.argv) != 3:
        return 64
    layout = StoreLayout.at(Path(sys.argv[1]))
    transaction = Transaction.model_validate_json(
        Path(sys.argv[2]).read_bytes(), strict=True
    )
    commit_transaction(layout, transaction)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
