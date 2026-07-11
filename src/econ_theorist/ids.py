"""Stable local identifiers and timestamps for Phase 1 records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def new_id(prefix: str) -> str:
    """Return an opaque provider-neutral identifier with a readable class prefix."""

    if not prefix or not prefix[0].isalpha() or not prefix.replace("_", "").isalnum():
        raise ValueError("identifier prefix must begin with a letter and be alphanumeric")
    return f"{prefix}_{uuid.uuid4().hex}"


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp without platform-local time assumptions."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
