"""Named crash points used by recovery tests.

Faults are disabled unless an environment variable explicitly names a point.
The default enabled behavior is ``os._exit`` so subprocess tests exercise a
real abrupt interruption (no ``finally`` blocks or buffered I/O cleanup).
"""

from __future__ import annotations

import os
from collections.abc import Mapping


FAULT_POINT_ENV = "ECON_THEORIST_FAULT_POINT"
FAULT_MODE_ENV = "ECON_THEORIST_FAULT_MODE"
FAULT_EXIT_CODE_ENV = "ECON_THEORIST_FAULT_EXIT_CODE"
DEFAULT_FAULT_EXIT_CODE = 86

# Names locked by P1-03.  ``inject_fault`` also accepts future names so adding a
# commit step does not require weakening the injector itself.
KNOWN_FAULT_POINTS = (
    "after_staging",
    "after_artifact_installation",
    "after_transaction_installation",
    "after_temp_head_write",
    "after_head_replacement",
    "after_snapshot_write",
    "after_view_write",
)

_POINT_ENV_ALIASES = (FAULT_POINT_ENV, "ETAI_FAULT_POINT", "ECON_THEORIST_FAULT")


class InjectedFault(RuntimeError):
    """Raised when fault injection is explicitly configured in raise mode."""

    def __init__(self, point: str) -> None:
        self.point = point
        super().__init__(f"injected fault at {point}")


def _configured_points(environ: Mapping[str, str]) -> frozenset[str]:
    raw = next((environ[name] for name in _POINT_ENV_ALIASES if environ.get(name)), "")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def fault_enabled(
    point: str, *, environ: Mapping[str, str] | None = None
) -> bool:
    """Return whether ``point`` is selected by the current environment."""

    if not point or not point.strip():
        raise ValueError("fault point must be a non-empty name")
    env = os.environ if environ is None else environ
    selected = _configured_points(env)
    return point in selected or "*" in selected


def inject_fault(
    point: str, *, environ: Mapping[str, str] | None = None
) -> bool:
    """Abruptly exit or raise at a selected named fault point.

    ``ECON_THEORIST_FAULT_MODE=raise`` is useful for in-process unit tests.
    The default, ``exit``, calls :func:`os._exit` and is intended for child
    processes.  The function returns ``False`` when the point is disabled; an
    enabled point never returns.
    """

    env = os.environ if environ is None else environ
    if not fault_enabled(point, environ=env):
        return False

    mode = env.get(FAULT_MODE_ENV, "exit").strip().lower()
    if mode in {"raise", "exception"}:
        raise InjectedFault(point)
    if mode != "exit":
        raise ValueError(
            f"unsupported {FAULT_MODE_ENV}={mode!r}; expected 'exit' or 'raise'"
        )

    raw_code = env.get(FAULT_EXIT_CODE_ENV, str(DEFAULT_FAULT_EXIT_CODE))
    try:
        exit_code = int(raw_code)
    except ValueError as exc:
        raise ValueError(f"invalid fault exit code: {raw_code!r}") from exc
    if not 1 <= exit_code <= 255:
        raise ValueError("fault exit code must be between 1 and 255")
    os._exit(exit_code)


# Readable aliases for callers that prefer a checkpoint-like spelling.
fault_point = inject_fault
maybe_inject_fault = inject_fault
