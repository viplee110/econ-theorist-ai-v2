"""JSON transport for ``etai machine invoke``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .codec import canonical_json_bytes, sha256_digest
from .machine.dispatcher import MachineDispatcher
from .machine.models import DiagnosticV1, MachineRequestV1, MachineResponseV1


_OPERATIONS = frozenset(
    {
        "bootstrap.plan",
        "bootstrap.verify",
        "project.bind_or_initialize",
        "project.inspect",
        "navigation.plan_next",
        "run.open_or_resume",
        "egress.plan",
        "packet.deliver",
        "candidate.complete",
        "host.finish",
        "decision.confirm",
        "operation.inspect",
    }
)
_MAX_REQUEST_BYTES = 16 * 1024 * 1024


def _fallback_operation(data: bytes) -> str:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "operation.inspect"
    operation = value.get("operation") if isinstance(value, dict) else None
    return operation if operation in _OPERATIONS else "operation.inspect"


def invoke_machine_bytes(
    data: bytes, *, dispatcher: MachineDispatcher | None = None
) -> MachineResponseV1:
    """Parse exactly one request and always return one strict response object."""

    try:
        if not data:
            raise ValueError("machine request is empty")
        if len(data) > _MAX_REQUEST_BYTES:
            raise ValueError("machine request exceeds the 16 MiB transport limit")
        request = MachineRequestV1.model_validate_json(data, strict=True)
    except ValueError as exc:
        operation = (
            _fallback_operation(data)
            if len(data) <= _MAX_REQUEST_BYTES
            else "operation.inspect"
        )
        if isinstance(exc, ValidationError):
            failures = tuple(
                f"{'.'.join(str(item) for item in error['loc']) or '<root>'}:"
                f"{error['type']}"
                for error in exc.errors(
                    include_url=False, include_context=False
                )
            )
            message = "invalid machine request (" + "; ".join(failures) + ")"
        else:
            message = (str(exc) or "invalid machine request")[:2000]
        return MachineResponseV1(
            operation=operation,  # type: ignore[arg-type]
            request_digest=sha256_digest(data),
            outcome="error",
            mutated=False,
            diagnostics=(
                DiagnosticV1(
                    code="invalid_machine_request",
                    severity="error",
                    message=message,
                ),
            ),
        )
    return (dispatcher or MachineDispatcher()).dispatch(request)


def invoke_from_argument(request_argument: str) -> int:
    """Read stdin/path and emit exactly one canonical response JSON value."""

    try:
        if request_argument == "-":
            data = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
        else:
            with Path(request_argument).open("rb") as stream:
                data = stream.read(_MAX_REQUEST_BYTES + 1)
        response = invoke_machine_bytes(data)
    except OSError as exc:
        response = MachineResponseV1(
            operation="operation.inspect",
            request_digest=sha256_digest(request_argument.encode("utf-8")),
            outcome="error",
            mutated=False,
            diagnostics=(
                DiagnosticV1(
                    code="machine_request_unavailable",
                    severity="error",
                    message=str(exc),
                ),
            ),
        )
    sys.stdout.buffer.write(canonical_json_bytes(response) + b"\n")
    sys.stdout.buffer.flush()
    return 0 if response.outcome not in {"error", "conflict"} else 2


__all__ = ["invoke_from_argument", "invoke_machine_bytes"]
