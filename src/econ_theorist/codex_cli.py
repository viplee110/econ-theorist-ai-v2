"""JSON transport for the thin ``etai codex invoke`` bridge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .codec import canonical_json_bytes, sha256_digest
from .codex_bridge import (
    CODEX_BRIDGE_REQUEST_ADAPTER,
    CodexBridge,
    CodexBridgeResponseV1,
    codex_bridge_schema,
)
from .machine.models import DiagnosticV1


_MAX_REQUEST_BYTES = 16 * 1024 * 1024


def _fallback_operation(data: bytes) -> str:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "start_or_resume"
    operation = value.get("operation") if isinstance(value, dict) else None
    return (
        operation
        if operation
        in {
            "start_or_resume",
            "reframe.repair",
            "complete",
            "finish",
            "framing_team.open",
            "framing_team.publish_panel",
            "framing_team.publish_choice_review",
            "framing_team.apply_user_turn",
        }
        else "start_or_resume"
    )


def invoke_codex_bytes(
    data: bytes, *, bridge: CodexBridge | None = None
) -> CodexBridgeResponseV1:
    """Parse one versioned bridge request and return one strict response."""

    try:
        if not data:
            raise ValueError("Codex bridge request is empty")
        if len(data) > _MAX_REQUEST_BYTES:
            raise ValueError("Codex bridge request exceeds the 16 MiB transport limit")
        request = CODEX_BRIDGE_REQUEST_ADAPTER.validate_json(data, strict=True)
    except ValueError as exc:
        if isinstance(exc, ValidationError):
            failures = tuple(
                f"{'.'.join(str(item) for item in error['loc']) or '<root>'}:"
                f"{error['type']}"
                for error in exc.errors(include_url=False, include_context=False)
            )
            message = "invalid Codex bridge request (" + "; ".join(failures) + ")"
        else:
            message = (str(exc) or "invalid Codex bridge request")[:2000]
        return CodexBridgeResponseV1(
            operation=_fallback_operation(data),  # type: ignore[arg-type]
            request_digest=sha256_digest(data),
            outcome="error",
            mutated=False,
            diagnostics=(
                DiagnosticV1(
                    code="invalid_codex_bridge_request",
                    severity="error",
                    message=message,
                ),
            ),
        )
    return (bridge or CodexBridge()).invoke(request)


def invoke_from_argument(request_argument: str) -> int:
    """Read stdin/path and emit exactly one canonical response JSON value."""

    try:
        if request_argument == "-":
            data = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
        else:
            with Path(request_argument).open("rb") as stream:
                data = stream.read(_MAX_REQUEST_BYTES + 1)
        response = invoke_codex_bytes(data)
    except OSError as exc:
        response = CodexBridgeResponseV1(
            operation="start_or_resume",
            request_digest=sha256_digest(request_argument.encode("utf-8")),
            outcome="error",
            mutated=False,
            diagnostics=(
                DiagnosticV1(
                    code="codex_bridge_request_unavailable",
                    severity="error",
                    message=str(exc),
                ),
            ),
        )
    sys.stdout.buffer.write(canonical_json_bytes(response) + b"\n")
    sys.stdout.buffer.flush()
    return 0 if response.outcome not in {"error", "conflict"} else 2


def emit_schema(kind: str) -> int:
    """Emit the authoritative request, response, or combined JSON Schema."""

    value = codex_bridge_schema(kind)  # type: ignore[arg-type]
    sys.stdout.buffer.write(canonical_json_bytes(value) + b"\n")
    sys.stdout.buffer.flush()
    return 0


__all__ = ["emit_schema", "invoke_codex_bytes", "invoke_from_argument"]
