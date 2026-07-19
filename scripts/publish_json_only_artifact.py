"""Publish one model-authored JSON object without repairing its source bytes.

This helper is a transport boundary for noncanonical shadow tasks.  It accepts
one optional UTF-8 BOM, requires the remaining bytes to encode exactly one JSON
object, and publishes those BOM-free bytes without reserialization.  Prefixes,
suffixes, arrays, prose wrappers, and malformed JSON fail before the target is
created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


_UTF8_BOM = b"\xef\xbb\xbf"


class JsonOnlyArtifactError(ValueError):
    """The scratch source cannot be published as one JSON-only artifact."""


def _published_state(path: Path, data: bytes) -> str:
    """Return absent/exact/different for one prospective immutable target."""

    try:
        existing = path.read_bytes()
    except FileNotFoundError:
        return "absent"
    except OSError as exc:
        raise JsonOnlyArtifactError(
            f"cannot inspect published artifact: {path}"
        ) from exc
    return "exact" if existing == data else "different"


def _fsync_directory(path: Path) -> None:
    """Durably record the published name where the platform permits it."""

    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _reject_nonstandard_constant(value: str) -> None:
    raise JsonOnlyArtifactError(f"non-standard JSON constant is forbidden: {value}")


def _object_without_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise JsonOnlyArtifactError(f"duplicate JSON object key: {key!r}")
        value[key] = item
    return value


def validate_json_object_bytes(data: bytes) -> bytes:
    """Return the original BOM-free bytes after a syntax-only JSON-object check.

    The function deliberately does not trim whitespace, extract a JSON-looking
    substring, reserialize the object, validate a schema, or repair content.
    """

    if not isinstance(data, bytes):
        raise TypeError("JSON artifact source must be bytes")
    normalized = data[len(_UTF8_BOM) :] if data.startswith(_UTF8_BOM) else data
    try:
        text = normalized.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JsonOnlyArtifactError("source is not valid UTF-8") from exc
    try:
        value = json.loads(
            text,
            parse_constant=_reject_nonstandard_constant,
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except JsonOnlyArtifactError:
        raise
    except json.JSONDecodeError as exc:
        raise JsonOnlyArtifactError(
            "source is not one complete JSON object: "
            f"{exc.msg} at line {exc.lineno} column {exc.colno}"
        ) from exc
    if not isinstance(value, dict):
        raise JsonOnlyArtifactError("top-level JSON value must be an object")
    return normalized


def _write_new(path: Path, data: bytes) -> None:
    """Atomically publish bytes once, accepting only an exact replay."""

    path.parent.mkdir(parents=True, exist_ok=True)
    state = _published_state(path, data)
    if state == "exact":
        return
    if state == "different":
        raise JsonOnlyArtifactError(
            f"refusing to overwrite published artifact with different bytes: {path}"
        )

    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except OSError as exc:
            # Windows can report a losing no-overwrite race as generic OSError.
            state = _published_state(path, data)
            if state == "exact":
                return
            if state == "different":
                raise JsonOnlyArtifactError(
                    "refusing to overwrite concurrently published artifact "
                    f"with different bytes: {path}"
                ) from exc
            raise JsonOnlyArtifactError(
                f"cannot atomically publish artifact: {path}"
            ) from exc
        try:
            _fsync_directory(path.parent)
        except OSError as exc:
            raise JsonOnlyArtifactError(
                f"cannot durably publish artifact: {path}"
            ) from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def publish_json_only_artifact(source: Path, target: Path) -> bytes:
    """Validate ``source`` and publish its exact BOM-free bytes to a new target."""

    try:
        source_data = source.read_bytes()
    except OSError as exc:
        raise JsonOnlyArtifactError(f"cannot read scratch source: {source}") from exc
    published = validate_json_object_bytes(source_data)
    _write_new(target, published)
    return published


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        published = publish_json_only_artifact(args.source, args.target)
    except JsonOnlyArtifactError as exc:
        print(f"INVALID_JSON_ARTIFACT: {exc}", file=sys.stderr)
        return 2
    print(
        "PUBLISH_OK "
        f"{hashlib.sha256(published).hexdigest()} {len(published)} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
