"""Deterministic canonical JSON and SHA-256 helpers.

Canonical transaction bytes never contain their own digest.  The digest is a
property of the bytes and is stored as the object name and canonical head.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

from pydantic import BaseModel

from .errors import CanonicalEncodingError

SHA256_HEX_LENGTH = 64
_TRANSACTION_DIGEST_FIELDS = frozenset({"digest", "transaction_digest"})


def _canonical_data(value: Any, *, path: str = "$") -> Any:
    """Return a JSON-native tree or fail closed.

    Floats are deliberately excluded, including finite floats.  This avoids
    cross-runtime number-format questions and automatically rejects NaN and
    infinities.  Theory-specific decimal quantities must be represented by an
    explicit string or rational object instead.
    """

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", by_alias=True, exclude_none=False)

    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        raise CanonicalEncodingError(f"float is forbidden at {path}")

    if isinstance(value, Enum):
        return _canonical_data(value.value, path=path)

    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalEncodingError(
                    f"canonical JSON object key at {path} must be a string"
                )
            normalized[key] = _canonical_data(item, path=f"{path}.{key}")
        return normalized

    if isinstance(value, (bytes, bytearray, memoryview)):
        raise CanonicalEncodingError(f"binary value is forbidden at {path}")

    if isinstance(value, Sequence):
        return [
            _canonical_data(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]

    raise CanonicalEncodingError(
        f"unsupported canonical value {type(value).__name__} at {path}"
    )


def ensure_canonical_data(value: Any) -> Any:
    """Validate and normalize a value to the accepted JSON-native subset."""

    return _canonical_data(value)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize *value* as deterministic UTF-8 JSON without a trailing LF."""

    normalized = _canonical_data(value)
    try:
        text = json.dumps(
            normalized,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return text.encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CanonicalEncodingError(str(exc)) from exc


def sha256_digest(data: bytes | bytearray | memoryview) -> str:
    """Return the raw 64-character lowercase SHA-256 hex digest."""

    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("sha256_digest requires a bytes-like value")
    return hashlib.sha256(bytes(data)).hexdigest()


def object_digest(value: Any) -> str:
    """Return the SHA-256 digest of a value's canonical JSON bytes."""

    return sha256_digest(canonical_json_bytes(value))


def transaction_bytes(transaction: Any) -> bytes:
    """Serialize a canonical transaction while rejecting embedded digests.

    Failing on an embedded digest is intentional.  Silently deleting it could
    make the caller believe different input was committed than the bytes that
    were actually hashed.
    """

    normalized = _canonical_data(transaction)
    if not isinstance(normalized, dict):
        raise CanonicalEncodingError("a transaction must encode as a JSON object")
    embedded = sorted(_TRANSACTION_DIGEST_FIELDS.intersection(normalized))
    if embedded:
        names = ", ".join(embedded)
        raise CanonicalEncodingError(
            f"transaction digest is external to canonical bytes; remove: {names}"
        )
    return canonical_json_bytes(normalized)


def transaction_digest(transaction: Any) -> str:
    """Return the canonical transaction revision for *transaction*."""

    return sha256_digest(transaction_bytes(transaction))


def is_sha256_digest(value: object) -> bool:
    """Return whether *value* is a canonical raw SHA-256 hex digest."""

    if not isinstance(value, str) or len(value) != SHA256_HEX_LENGTH:
        return False
    return all(character in "0123456789abcdef" for character in value)
