"""Capture one public Codex bridge invocation without host-output truncation.

This is a pilot harness, not an installed product interface. Child stdout and
stderr go straight to files so a terminal or agent transport never carries the
raw response. Captures are local evidence and require an explicit freeze,
secret scan, and bounded redaction before publication.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from pydantic import ValidationError

from econ_theorist.codex_bridge import (
    CODEX_BRIDGE_REQUEST_ADAPTER,
    CodexBridgeResponseV1,
)
from econ_theorist.codec import canonical_json_bytes


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exclusive_output(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"capture output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def _inside(root: Path, path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must be inside the selected pilot root") from exc
    return resolved


def _validate_distinct_outputs(paths: tuple[Path, ...]) -> None:
    if len(set(paths)) != len(paths):
        raise ValueError("stdout, stderr, and metadata paths must be distinct")
    for index, left in enumerate(paths):
        for right in paths[index + 1 :]:
            if left in right.parents or right in left.parents:
                raise ValueError("capture output paths cannot contain one another")


def _bounded_validation_error(exc: ValidationError) -> str:
    """Describe invalid bridge bytes without copying response values to metadata."""

    issues: list[str] = []
    for issue in exc.errors(include_input=False, include_url=False)[:8]:
        location = ".".join(str(part) for part in issue["loc"]) or "response"
        issues.append(f"{location}: {issue['msg']}")
    remainder = exc.error_count() - len(issues)
    if remainder > 0:
        issues.append(f"... plus {remainder} validation issue(s)")
    return "; ".join(issues)


def _capture_exit_code(child_exit_code: int, bridge_response_valid: bool) -> int:
    if child_exit_code != 0:
        return child_exit_code
    return 0 if bridge_response_valid else 3


def capture_invocation(
    command: Sequence[str],
    *,
    request_path: Path,
    project_root: Path,
    local_app_data: Path,
    stdout_path: Path,
    stderr_path: Path,
    metadata_path: Path,
) -> tuple[int, dict[str, Any]]:
    """Run one command with isolated state and direct, immutable file capture."""

    root = project_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("selected pilot root must be a directory")
    request = request_path.resolve(strict=True)
    request_bytes = request.read_bytes()
    parsed_request = CODEX_BRIDGE_REQUEST_ADAPTER.validate_json(
        request_bytes, strict=True
    )
    canonical_request_sha256 = _sha256(canonical_json_bytes(parsed_request))
    declared_root = Path(parsed_request.project_root).expanduser()
    if not declared_root.is_absolute():
        declared_root = root / declared_root
    if declared_root.resolve(strict=True) != root:
        raise ValueError("request project_root does not match the selected pilot root")

    isolated = _inside(root, local_app_data, label="state-isolation root")
    outputs = tuple(
        _inside(root, path, label="capture output")
        for path in (stdout_path, stderr_path, metadata_path)
    )
    _validate_distinct_outputs(outputs)
    if any(
        path == isolated or path in isolated.parents or isolated in path.parents
        for path in outputs
    ):
        raise ValueError("capture outputs cannot overlap the state-isolation root")
    for path in outputs:
        _exclusive_output(path)

    # Precreate the exact engine fallbacks for both supported platform families.
    (isolated / "EconTheoristAI" / "operational" / "v1").mkdir(
        parents=True, exist_ok=True
    )
    isolated_home = isolated / "home"
    isolated_xdg_state = isolated / "xdg-state"
    (isolated_home / ".local" / "state" / "econ-theorist" / "operational" / "v1").mkdir(
        parents=True, exist_ok=True
    )
    (isolated_xdg_state / "econ-theorist" / "operational" / "v1").mkdir(
        parents=True, exist_ok=True
    )

    environment = os.environ.copy()
    environment["LOCALAPPDATA"] = str(isolated)
    environment["HOME"] = str(isolated_home)
    environment["XDG_STATE_HOME"] = str(isolated_xdg_state)
    started_at = _utc_now()
    with outputs[0].open("xb") as stdout_stream, outputs[1].open(
        "xb"
    ) as stderr_stream:
        completed = subprocess.run(
            list(command),
            cwd=root,
            env=environment,
            input=request_bytes,
            stdout=stdout_stream,
            stderr=stderr_stream,
            check=False,
        )
    ended_at = _utc_now()

    stdout_bytes = outputs[0].read_bytes()
    stderr_bytes = outputs[1].read_bytes()
    try:
        source_after = request.read_bytes()
    except OSError:
        source_after = None
    schema_response: CodexBridgeResponseV1 | None = None
    response: CodexBridgeResponseV1 | None = None
    parsed_response: dict[str, Any] | None = None
    json_shape_error: str | None = None
    bridge_validation_error: str | None = None
    response_binding_error: str | None = None
    try:
        if stdout_bytes.count(b"\n") != 1 or not stdout_bytes.endswith(b"\n"):
            raise ValueError("stdout is not exactly one newline-terminated JSON value")
        parsed = json.loads(stdout_bytes)
        if not isinstance(parsed, dict):
            raise ValueError("stdout JSON is not an object")
        parsed_response = parsed
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        json_shape_error = str(exc)
    if parsed_response is not None:
        try:
            schema_response = CodexBridgeResponseV1.model_validate_json(
                stdout_bytes, strict=True
            )
        except ValidationError as exc:
            bridge_validation_error = _bounded_validation_error(exc)
    if schema_response is not None:
        binding_errors: list[str] = []
        if schema_response.operation != parsed_request.operation:
            binding_errors.append(
                "response operation does not match the captured request"
            )
        if schema_response.request_digest != canonical_request_sha256:
            binding_errors.append(
                "response request_digest does not match the canonical request"
            )
        if binding_errors:
            response_binding_error = "; ".join(binding_errors)
        else:
            response = schema_response

    metadata: dict[str, Any] = {
        "capture_schema": "econ-theorist/codex-invocation-capture/v1",
        "started_at": started_at,
        "ended_at": ended_at,
        "command": list(command),
        "project_root": str(root),
        "source_request_path": str(request),
        "request_transport": "stdin",
        "request_bytes": len(request_bytes),
        "request_sha256": _sha256(request_bytes),
        "canonical_request_sha256": canonical_request_sha256,
        "source_request_sha256_after": (
            None if source_after is None else _sha256(source_after)
        ),
        "source_request_changed_after_read": source_after != request_bytes,
        "stdout_path": str(outputs[0]),
        "stdout_bytes": len(stdout_bytes),
        "stdout_sha256": _sha256(stdout_bytes),
        "stderr_path": str(outputs[1]),
        "stderr_bytes": len(stderr_bytes),
        "stderr_sha256": _sha256(stderr_bytes),
        "localappdata": str(isolated),
        "home": str(isolated_home),
        "xdg_state_home": str(isolated_xdg_state),
        "exit_code": completed.returncode,
        "stdout_json_object_valid": parsed_response is not None,
        "bridge_schema_valid": schema_response is not None,
        "bridge_response_valid": response is not None,
        "response_valid": response is not None,
        "json_shape_error": json_shape_error,
        "bridge_validation_error": bridge_validation_error,
        "response_binding_error": response_binding_error,
        "capture_error": (
            json_shape_error or bridge_validation_error or response_binding_error
        ),
    }
    if response is not None:
        response_data = response.model_dump(mode="json")
        metadata["response"] = {
            key: response_data.get(key)
            for key in (
                "operation",
                "outcome",
                "mutated",
                "project_id",
                "head",
                "route_run_id",
                "request_digest",
            )
        }
    with outputs[2].open("xb") as stream:
        stream.write(
            (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode(
                "utf-8"
            )
        )
    return completed.returncode, metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture one etai codex response directly to evidence files"
    )
    parser.add_argument("--etai", required=True, help="exact installed etai executable")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--local-appdata", required=True, type=Path)
    parser.add_argument("--stdout", required=True, type=Path)
    parser.add_argument("--stderr", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    exit_code, metadata = capture_invocation(
        [args.etai, "codex", "invoke", "--request", "-"],
        request_path=args.request,
        project_root=args.project_root,
        local_app_data=args.local_appdata,
        stdout_path=args.stdout,
        stderr_path=args.stderr,
        metadata_path=args.metadata,
    )
    summary = {
        "exit_code": exit_code,
        "response_valid": metadata["response_valid"],
        "stdout_bytes": metadata["stdout_bytes"],
        "stdout_sha256": metadata["stdout_sha256"],
        "outcome": (metadata.get("response") or {}).get("outcome"),
    }
    print(json.dumps(summary, separators=(",", ":")))
    return _capture_exit_code(exit_code, metadata["bridge_response_valid"])


if __name__ == "__main__":
    raise SystemExit(main())
