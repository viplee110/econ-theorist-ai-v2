"""Run the complete regression suite except the three hour-scale gold chains."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EXCLUDED_MODULES = frozenset(
    {
        "test_phase2_gold_runtime_chain",
        "test_phase3_gold_runtime_chain",
        "test_phase4_gold_runtime_chain",
    }
)


def _non_long(suite: unittest.TestSuite) -> unittest.TestSuite:
    selected = unittest.TestSuite()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            nested = _non_long(item)
            if nested.countTestCases():
                selected.addTest(nested)
            continue
        module = item.__class__.__module__.rsplit(".", 1)[-1]
        if module not in EXCLUDED_MODULES:
            selected.addTest(item)
    return selected


def main() -> int:
    discovered = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), top_level_dir=str(ROOT)
    )
    selected = _non_long(discovered)
    print(
        "non-long regression selection: "
        f"{selected.countTestCases()} tests; excluded="
        + ",".join(sorted(EXCLUDED_MODULES)),
        file=sys.stderr,
    )
    result = unittest.TextTestRunner(verbosity=1).run(selected)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
