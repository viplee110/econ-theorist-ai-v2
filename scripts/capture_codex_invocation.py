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
from econ_theorist.machine.completion import (
    CandidateTransactionValidationError,
    candidate_source_digest,
)
from econ_theorist.machine.egress import read_bound_work_packet
from econ_theorist.machine.operational import ProjectOperationalLayout
from econ_theorist.runtime.layout import StoreLayout


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
        raise ValueError("capture output paths must be distinct")
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
    candidate_source_path: Path | None = None,
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
    candidate_source: Path | None = None
    candidate_bytes: bytes | None = None
    candidate_canonical_digest: str | None = None
    candidate_preflight_validation_error: str | None = None
    if parsed_request.operation == "complete":
        if parsed_request.action == "commit_staged":
            if candidate_source_path is not None:
                raise ValueError(
                    "candidate_source_path is invalid when complete reads staged bytes"
                )
        else:
            if candidate_source_path is None:
                raise ValueError(
                    "candidate_source_path is required when a complete request "
                    "reads host source"
                )
            expected_candidate = _inside(
                root,
                root
                / ".econ-theorist"
                / "staging"
                / parsed_request.route_run_id
                / "candidate.json",
                label="route-bound candidate source",
            )
            declared_candidate = (
                expected_candidate
                if parsed_request.transaction_path is None
                else Path(parsed_request.transaction_path).expanduser()
            )
            if not declared_candidate.is_absolute():
                declared_candidate = root / declared_candidate
            declared_candidate = _inside(
                root,
                declared_candidate,
                label="complete transaction path",
            )
            if declared_candidate != expected_candidate:
                raise ValueError(
                    "complete transaction_path differs from the route-bound "
                    "candidate source"
                )
            candidate_source = _inside(
                root,
                candidate_source_path,
                label="candidate source",
            )
            if candidate_source != expected_candidate:
                raise ValueError(
                    "candidate_source_path differs from the complete request's "
                    "route-bound candidate source"
                )
            candidate_bytes = candidate_source.read_bytes()
            operational = ProjectOperationalLayout.at(StoreLayout.at(root))
            packet = read_bound_work_packet(
                operational,
                parsed_request.route_run_id,
                parsed_request.work_packet_hash,
            )
            try:
                candidate_canonical_digest = candidate_source_digest(
                    StoreLayout.at(root), packet, candidate_source
                )
            except CandidateTransactionValidationError as exc:
                candidate_preflight_validation_error = (
                    "CandidateTransactionValidationError("
                    f"issue_count={exc.issue_count},truncated={exc.truncated})"
                )
            if candidate_source.read_bytes() != candidate_bytes:
                raise ValueError(
                    "candidate source changed during pre-invocation binding"
                )
    elif candidate_source_path is not None:
        raise ValueError("candidate_source_path is valid only for complete requests")

    isolated = _inside(root, local_app_data, label="state-isolation root")
    primary_outputs = tuple(
        _inside(root, path, label="capture output")
        for path in (stdout_path, stderr_path, metadata_path)
    )
    request_capture = _inside(
        root,
        primary_outputs[2].with_name(
            f"{primary_outputs[2].stem}-captured-request.json"
        ),
        label="captured request output",
    )
    candidate_capture = (
        None
        if candidate_source_path is None
        else _inside(
            root,
            primary_outputs[2].with_name(
                f"{primary_outputs[2].stem}-captured-candidate.json"
            ),
            label="captured candidate output",
        )
    )
    outputs = (
        *primary_outputs,
        request_capture,
        *((candidate_capture,) if candidate_capture is not None else ()),
    )
    _validate_distinct_outputs(outputs)
    if request_capture == request:
        raise ValueError("captured request output must differ from its source")
    if candidate_capture is not None and candidate_capture == candidate_source:
        raise ValueError("captured candidate output must differ from its source")
    if any(
        path == isolated or path in isolated.parents or isolated in path.parents
        for path in outputs
    ):
        raise ValueError("capture outputs cannot overlap the state-isolation root")
    for path in outputs:
        _exclusive_output(path)
    with request_capture.open("xb") as stream:
        stream.write(request_bytes)
    if candidate_capture is not None and candidate_bytes is not None:
        with candidate_capture.open("xb") as stream:
            stream.write(candidate_bytes)

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
    with primary_outputs[0].open("xb") as stdout_stream, primary_outputs[1].open(
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

    stdout_bytes = primary_outputs[0].read_bytes()
    stderr_bytes = primary_outputs[1].read_bytes()
    try:
        source_after = request.read_bytes()
    except OSError:
        source_after = None
    try:
        candidate_after = (
            None if candidate_source is None else candidate_source.read_bytes()
        )
    except OSError:
        candidate_after = None
    candidate_changed = (
        None if candidate_bytes is None else candidate_after != candidate_bytes
    )
    schema_response: CodexBridgeResponseV1 | None = None
    response: CodexBridgeResponseV1 | None = None
    parsed_response: dict[str, Any] | None = None
    json_shape_error: str | None = None
    bridge_validation_error: str | None = None
    response_binding_error: str | None = None
    candidate_digest_matches_response: bool | None = None
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
        if candidate_changed:
            binding_errors.append(
                "candidate source changed after the pre-invocation capture"
            )
        if candidate_source is not None and schema_response.completion is not None:
            response_candidate_digest = schema_response.completion.candidate_digest
            if response_candidate_digest is None:
                candidate_digest_matches_response = False
                binding_errors.append(
                    "completion response omits the source candidate digest"
                )
            elif candidate_canonical_digest is None:
                candidate_digest_matches_response = False
                binding_errors.append(
                    "completion candidate digest cannot bind to the invalid "
                    "pre-invocation source"
                )
            elif response_candidate_digest != candidate_canonical_digest:
                candidate_digest_matches_response = False
                binding_errors.append(
                    "completion candidate digest differs from the pre-invocation "
                    "source"
                )
            else:
                candidate_digest_matches_response = True
        if binding_errors:
            response_binding_error = "; ".join(binding_errors)
        else:
            response = schema_response

    metadata: dict[str, Any] = {
        "capture_schema": "econ-theorist/codex-invocation-capture/v2",
        "started_at": started_at,
        "ended_at": ended_at,
        "command": list(command),
        "project_root": str(root),
        "source_request_path": str(request),
        "request_transport": "stdin",
        "request_bytes": len(request_bytes),
        "request_sha256": _sha256(request_bytes),
        "canonical_request_sha256": canonical_request_sha256,
        "captured_request_path": str(request_capture),
        "captured_request_sha256": _sha256(request_capture.read_bytes()),
        "source_request_sha256_after": (
            None if source_after is None else _sha256(source_after)
        ),
        "source_request_changed_after_read": source_after != request_bytes,
        "candidate_source_path": (
            None if candidate_source is None else str(candidate_source)
        ),
        "candidate_bytes": (
            None if candidate_bytes is None else len(candidate_bytes)
        ),
        "candidate_sha256": (
            None if candidate_bytes is None else _sha256(candidate_bytes)
        ),
        "candidate_canonical_digest_before": candidate_canonical_digest,
        "candidate_preflight_validation_error": (
            candidate_preflight_validation_error
        ),
        "captured_candidate_path": (
            None if candidate_capture is None else str(candidate_capture)
        ),
        "captured_candidate_sha256": (
            None
            if candidate_capture is None
            else _sha256(candidate_capture.read_bytes())
        ),
        "source_candidate_sha256_after": (
            None if candidate_after is None else _sha256(candidate_after)
        ),
        "source_candidate_changed_after_read": candidate_changed,
        "candidate_digest_matches_response": candidate_digest_matches_response,
        "stdout_path": str(primary_outputs[0]),
        "stdout_bytes": len(stdout_bytes),
        "stdout_sha256": _sha256(stdout_bytes),
        "stderr_path": str(primary_outputs[1]),
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
    with primary_outputs[2].open("xb") as stream:
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
    parser.add_argument(
        "--candidate-source",
        type=Path,
        help="required pre-invocation raw candidate source for complete requests",
    )
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
        candidate_source_path=args.candidate_source,
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
