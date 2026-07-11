"""Integrity-preserving file primitives for the local runtime store."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import Any

from ..errors import (
    DigestCollisionError,
    HashMismatchError,
    IntegrityError,
    RuntimeStoreError,
)
from .faults import inject_fault
from .layout import (
    StoreLayout,
    assert_safe_store_path,
    path_entry_exists,
)


_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_NAMESPACE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


StoreError = RuntimeStoreError


class InvalidDigest(IntegrityError, ValueError):
    """A digest is not a canonical SHA-256 identifier."""


class DigestMismatch(HashMismatchError):
    """Proposed bytes do not match their declared digest."""

    def __init__(
        self,
        declared: str,
        actual: str,
        *,
        quarantine_report: Path | None = None,
    ) -> None:
        self.declared = declared
        self.actual = actual
        self.quarantine_report = quarantine_report
        super().__init__(f"declared sha256 {declared} does not match bytes {actual}")


class ImmutableObjectConflict(DigestCollisionError):
    """A content-addressed target already contains different bytes."""

    def __init__(
        self,
        path: Path,
        expected_digest: str,
        existing_digest: str,
        *,
        quarantine_report: Path | None = None,
    ) -> None:
        self.path = path
        self.expected_digest = expected_digest
        self.existing_digest = existing_digest
        self.quarantine_report = quarantine_report
        super().__init__(
            f"immutable object conflict at {path}: expected {expected_digest}, "
            f"found bytes hashing to {existing_digest}"
        )


class ExistingObjectCorrupt(ImmutableObjectConflict):
    """An existing filename does not match the digest encoded in its path."""


class ContentCollision(ImmutableObjectConflict):
    """Distinct bytes claim one valid digest (a simulated/real collision)."""


class ObjectNotFound(StoreError, FileNotFoundError):
    """A requested immutable object does not exist."""


class AtomicWriteError(StoreError):
    """A replaceable runtime file could not be written atomically."""


class HeadFormatError(IntegrityError):
    """The canonical head is not exactly one raw lowercase SHA-256 digest."""


class HeadChanged(StoreError):
    """The head differs from the base re-read by the caller under the lock."""

    def __init__(self, expected: str | None, actual: str | None) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"stale base: expected head {expected!r}, found {actual!r}")


@dataclass(frozen=True, slots=True)
class ObjectInstall:
    """Result of an immutable object installation."""

    namespace: str
    digest: str
    path: Path
    created: bool

    @property
    def qualified_digest(self) -> str:
        return f"sha256:{self.digest}"


def sha256_hex(data: bytes) -> str:
    """Return the lowercase, unprefixed SHA-256 digest of ``data``."""

    return hashlib.sha256(data).hexdigest()


def normalize_sha256(digest: str) -> str:
    """Normalize ``sha256:<hex>`` or ``<hex>`` to lowercase ``<hex>``."""

    if not isinstance(digest, str):
        raise InvalidDigest(f"digest must be text, got {type(digest).__name__}")
    value = digest.strip().lower()
    if value.startswith("sha256:"):
        value = value[7:]
    if _SHA256_RE.fullmatch(value) is None:
        raise InvalidDigest(f"invalid SHA-256 digest: {digest!r}")
    return value


def _raw_sha256(digest: str, *, label: str) -> str:
    """Require the canonical spelling used by the on-disk head protocol."""

    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise InvalidDigest(f"{label} must be exactly 64 lowercase hex characters")
    return digest


def _safe_namespace(namespace: str) -> str:
    if not isinstance(namespace, str) or _NAMESPACE_RE.fullmatch(namespace) is None:
        raise ValueError(f"unsafe object namespace: {namespace!r}")
    return namespace


def fsync_directory(directory: str | Path) -> None:
    """Durably record a directory update where the platform permits it."""

    if os.name == "nt":
        # Opening directories for fsync is not supported by ordinary Win32
        # handles.  ReplaceFile/MoveFileEx durability is delegated to Windows.
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(directory, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_temp_file(parent: Path, basename: str, data: bytes, mode: int) -> Path:
    assert_safe_store_path(
        parent,
        parent,
        expected="directory",
        allow_missing=False,
    )
    fd, raw_path = tempfile.mkstemp(prefix=f".{basename}.tmp-", dir=parent)
    temp_path = Path(raw_path)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return temp_path
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        temp_path.unlink(missing_ok=True)
        raise


def atomic_write_bytes(
    path: str | Path,
    data: bytes,
    *,
    mode: int = 0o600,
    before_replace_fault: str | Callable[[], None] | None = None,
    after_replace_fault: str | Callable[[], None] | None = None,
) -> None:
    """Write bytes by fsyncing a same-directory temp and replacing atomically."""

    if not isinstance(data, bytes):
        raise TypeError("atomic_write_bytes requires bytes")
    target = Path(path)
    assert_safe_store_path(
        target.parent,
        target,
        expected="file",
        allow_missing=True,
    )
    temp_path = _write_temp_file(target.parent, target.name, data, mode)
    try:
        if callable(before_replace_fault):
            before_replace_fault()
        elif before_replace_fault:
            inject_fault(before_replace_fault)
        os.replace(temp_path, target)
        fsync_directory(target.parent)
        if callable(after_replace_fault):
            after_replace_fault()
        elif after_replace_fault:
            inject_fault(after_replace_fault)
    except BaseException as exc:
        if isinstance(exc, (SystemExit, KeyboardInterrupt)) or not isinstance(
            exc, OSError
        ):
            raise
        raise AtomicWriteError(f"atomic write failed for {target}: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


def atomic_write_text(
    path: str | Path,
    text: str,
    *,
    encoding: str = "utf-8",
    mode: int = 0o600,
    before_replace_fault: str | Callable[[], None] | None = None,
    after_replace_fault: str | Callable[[], None] | None = None,
) -> None:
    """Text wrapper around :func:`atomic_write_bytes`."""

    atomic_write_bytes(
        path,
        text.encode(encoding),
        mode=mode,
        before_replace_fault=before_replace_fault,
        after_replace_fault=after_replace_fault,
    )


class ObjectStore:
    """Immutable content-addressed namespaces beneath one store root."""

    def __init__(self, root: str | Path | StoreLayout) -> None:
        self.root = (
            root.store_root
            if isinstance(root, StoreLayout)
            else Path(root).expanduser().absolute()
        )
        self.quarantine_reports_dir = self.root / "quarantine" / "reports"

    def namespace_root(self, namespace: str) -> Path:
        return self.root / _safe_namespace(namespace) / "sha256"

    def path_for(self, namespace: str, digest: str) -> Path:
        return self.namespace_root(namespace) / normalize_sha256(digest)

    def _ensure_directory(self, directory: Path) -> None:
        """Create one store descendant, checking every component in order."""

        assert_safe_store_path(
            self.root,
            self.root,
            expected="directory",
            allow_missing=False,
        )
        relative = directory.relative_to(self.root)
        current = self.root
        for component in relative.parts:
            current = current / component
            assert_safe_store_path(
                self.root,
                current,
                expected="directory",
                allow_missing=True,
            )
            if not path_entry_exists(current):
                current.mkdir(exist_ok=False)
            assert_safe_store_path(
                self.root,
                current,
                expected="directory",
                allow_missing=False,
            )

    def _validate_target(self, target: Path, *, allow_missing: bool) -> None:
        assert_safe_store_path(
            self.root,
            target.parent,
            expected="directory",
            allow_missing=False,
        )
        assert_safe_store_path(
            self.root,
            target,
            expected="file",
            allow_missing=allow_missing,
        )

    def _report(
        self,
        *,
        reason: str,
        namespace: str,
        expected_digest: str,
        incoming_digest: str | None,
        incoming_size: int | None,
        existing_digest: str | None,
        existing_size: int | None,
        target: Path,
    ) -> Path:
        self._ensure_directory(self.quarantine_reports_dir)
        report_id = f"q-{time.time_ns()}-{os.getpid()}-{uuid.uuid4().hex}"
        try:
            relative_target = target.relative_to(self.root).as_posix()
        except ValueError:
            relative_target = target.name
        report = {
            "schema": "econ-theorist/quarantine-report/v1",
            "report_id": report_id,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "namespace": namespace,
            "expected_digest": f"sha256:{expected_digest}",
            "incoming_digest": (
                f"sha256:{incoming_digest}" if incoming_digest is not None else None
            ),
            "incoming_size": incoming_size,
            "existing_digest": (
                f"sha256:{existing_digest}" if existing_digest is not None else None
            ),
            "existing_size": existing_size,
            "target": relative_target,
            "canonical_head_modified": False,
            "target_overwritten": False,
        }
        encoded = (
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        path = self.quarantine_reports_dir / f"{report_id}.json"
        atomic_write_bytes(path, encoded)
        return path

    def _verify_existing(
        self,
        namespace: str,
        digest: str,
        target: Path,
        incoming: bytes | None,
    ) -> ObjectInstall:
        self._validate_target(target, allow_missing=False)
        try:
            existing = target.read_bytes()
        except FileNotFoundError:
            raise
        existing_digest = sha256_hex(existing)

        if incoming is not None and existing == incoming:
            return ObjectInstall(namespace, digest, target, created=False)

        reason = (
            "existing_object_corrupt"
            if existing_digest != digest
            else "content_digest_collision"
        )
        report_path = self._report(
            reason=reason,
            namespace=namespace,
            expected_digest=digest,
            incoming_digest=sha256_hex(incoming) if incoming is not None else None,
            incoming_size=len(incoming) if incoming is not None else None,
            existing_digest=existing_digest,
            existing_size=len(existing),
            target=target,
        )
        error_type = ExistingObjectCorrupt if existing_digest != digest else ContentCollision
        raise error_type(
            target,
            digest,
            existing_digest,
            quarantine_report=report_path,
        )

    def install_bytes(
        self,
        namespace: str,
        digest: str | None,
        data: bytes,
    ) -> ObjectInstall:
        """Install immutable bytes without ever replacing an existing target.

        An existing byte-for-byte match is an idempotent success.  Any mismatch
        creates an auditable quarantine report and raises an integrity error.
        """

        namespace = _safe_namespace(namespace)
        if not isinstance(data, bytes):
            raise TypeError("content-addressed objects must be bytes")
        actual = sha256_hex(data)
        declared = actual if digest is None else normalize_sha256(digest)
        target = self.path_for(namespace, declared)

        if actual != declared:
            report_path = self._report(
                reason="declared_digest_mismatch",
                namespace=namespace,
                expected_digest=declared,
                incoming_digest=actual,
                incoming_size=len(data),
                existing_digest=None,
                existing_size=None,
                target=target,
            )
            raise DigestMismatch(declared, actual, quarantine_report=report_path)

        self._ensure_directory(target.parent)
        self._validate_target(target, allow_missing=True)
        if path_entry_exists(target):
            return self._verify_existing(namespace, declared, target, data)

        # A hard-link publication is atomic and, unlike os.replace, cannot
        # overwrite a winner that appears between the existence check and the
        # publish operation.  Both links are on the same filesystem/directory.
        temp_path = _write_temp_file(target.parent, target.name, data, 0o600)
        try:
            try:
                os.link(temp_path, target)
                fsync_directory(target.parent)
                return ObjectInstall(namespace, declared, target, created=True)
            except FileExistsError:
                return self._verify_existing(namespace, declared, target, data)
            except OSError as exc:
                # Some Windows errors arrive as generic OSError even when the
                # target won the race.  Verify it; otherwise fail closed.
                if path_entry_exists(target):
                    return self._verify_existing(namespace, declared, target, data)
                raise AtomicWriteError(
                    f"cannot publish immutable object {target}: {exc}"
                ) from exc
        finally:
            temp_path.unlink(missing_ok=True)

    def install_object(
        self,
        namespace: str,
        obj: Any,
        digest: str | None = None,
    ) -> ObjectInstall:
        """Canonical-JSON convenience wrapper, imported lazily to avoid cycles."""

        from ..codec import canonical_json_bytes

        return self.install_bytes(namespace, digest, canonical_json_bytes(obj))

    def read_bytes(
        self, namespace: str, digest: str, *, verify: bool = True
    ) -> bytes:
        target = self.path_for(namespace, digest)
        try:
            self._validate_target(target, allow_missing=False)
        except FileNotFoundError as exc:
            raise ObjectNotFound(target) from exc
        try:
            data = target.read_bytes()
        except FileNotFoundError as exc:
            raise ObjectNotFound(target) from exc
        if verify and sha256_hex(data) != normalize_sha256(digest):
            self._verify_existing(
                _safe_namespace(namespace), normalize_sha256(digest), target, None
            )
        return data

    def verify(self, namespace: str, digest: str) -> Path:
        """Verify one object and return its path."""

        self.read_bytes(namespace, digest, verify=True)
        return self.path_for(namespace, digest)


class HeadStore:
    """Strict reader and atomic writer for the single canonical head pointer.

    ``replace`` must be called while holding the project's commit lock.  Its
    expected-value check is a stale-base guard, not a portable CAS primitive.
    """

    def __init__(self, path: str | Path | StoreLayout) -> None:
        if isinstance(path, StoreLayout):
            self.path = path.main_ref
            self._root = path.store_root
        else:
            self.path = Path(path).expanduser().absolute()
            self._root = self.path.parent

    def _validate_path(self, *, allow_missing: bool) -> None:
        assert_safe_store_path(
            self._root,
            self.path,
            expected="file",
            allow_missing=allow_missing,
        )

    def read(self) -> str | None:
        try:
            self._validate_path(allow_missing=True)
        except FileNotFoundError:
            return None
        if not path_entry_exists(self.path):
            return None
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return None
        if re.fullmatch(rb"[0-9a-f]{64}", raw) is None:
            raise HeadFormatError(f"head is not one canonical digest: {self.path}")
        return raw.decode("ascii")

    def replace(self, expected: str | None, new: str) -> None:
        expected_digest = (
            None if expected is None else _raw_sha256(expected, label="expected head")
        )
        actual = self.read()
        if actual != expected_digest:
            raise HeadChanged(expected_digest, actual)
        new_digest = _raw_sha256(new, label="new head")
        atomic_write_text(
            self.path,
            new_digest,
            before_replace_fault="after_temp_head_write",
            after_replace_fault="after_head_replacement",
        )

    compare_and_replace = replace
