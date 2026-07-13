"""Noncanonical operational storage, content addressing, and idempotency."""

from __future__ import annotations

import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal

from pydantic import Field

from ..codec import canonical_json_bytes, sha256_digest
from ..errors import IntegrityError, RuntimeStoreError
from ..ids import utc_now
from ..models import Digest, StrictModel
from ..runtime.layout import (
    StoreLayout,
    UnsafeStorePath,
    assert_safe_store_path,
    path_entry_exists,
)
from ..runtime.lock import ExclusiveFileLock
from ..runtime.objects import fsync_directory
from .models import LedgerEventV1, MachineRequestV1, MachineResponseV1


_KEY_RE = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,127}")


class OperationalError(RuntimeStoreError):
    """A noncanonical operational record is missing, corrupt, or conflicting."""


class OperationKeyConflict(OperationalError):
    """One operation key was reused for different request bytes."""


class OperationInProgress(OperationalError):
    """A prior exact operation has no terminal result yet."""


class OperationReservationV1(StrictModel):
    reservation_schema: Literal["econ-theorist/operation-reservation/v1"] = (
        "econ-theorist/operation-reservation/v1"
    )
    operation_key: str
    operation: str
    request_digest: Digest
    reserved_at: str


class OperationTerminalV1(StrictModel):
    terminal_schema: Literal["econ-theorist/operation-terminal/v1"] = (
        "econ-theorist/operation-terminal/v1"
    )
    operation_key: str
    operation: str
    request_digest: Digest
    response_digest: Digest
    response: MachineResponseV1
    completed_at: str


def _safe_key(value: str) -> str:
    if not isinstance(value, str) or _KEY_RE.fullmatch(value) is None:
        raise OperationalError(f"unsafe operation key: {value!r}")
    return value


def _ensure_directory_tree(anchor: Path, target: Path) -> None:
    """Create ordinary descendants one component at a time."""

    anchor = anchor.absolute()
    target = target.absolute()
    try:
        relative = target.relative_to(anchor)
    except ValueError as exc:
        raise OperationalError(f"operational path escapes its anchor: {target}") from exc
    assert_safe_store_path(
        anchor, anchor, expected="directory", allow_missing=False
    )
    current = anchor
    for part in relative.parts:
        current = current / part
        assert_safe_store_path(
            anchor, current, expected="directory", allow_missing=True
        )
        if not path_entry_exists(current):
            try:
                current.mkdir(exist_ok=False)
            except FileExistsError:
                # A concurrent initializer may have created the exact ordinary
                # directory after our metadata check.  The mandatory safety
                # recheck below decides whether that winner is acceptable.
                pass
            else:
                fsync_directory(current.parent)
        assert_safe_store_path(
            anchor, current, expected="directory", allow_missing=False
        )


def _write_immutable(anchor: Path, path: Path, data: bytes) -> bool:
    """Publish exact bytes once; equal existing bytes are an idempotent hit."""

    if not isinstance(data, bytes):
        raise TypeError("immutable operational records must be bytes")
    _ensure_directory_tree(anchor, path.parent)
    try:
        assert_safe_store_path(
            anchor, path, expected="file", allow_missing=True
        )
    except UnsafeStorePath as exc:
        raise OperationalError(f"unsafe operational file: {path}") from exc

    if path_entry_exists(path):
        return _verify_immutable_bytes(anchor, path, data)

    temp_path = _write_immutable_temp(path.parent, path.name, data)
    try:
        try:
            # A same-directory hard-link publication is atomic and cannot
            # replace a winner that appears after the safety/existence check.
            # The final name therefore never exposes bytes while they are
            # still being written.
            os.link(temp_path, path)
        except FileExistsError:
            return _verify_immutable_bytes(anchor, path, data)
        except OSError as exc:
            # Windows can report a losing no-overwrite race as a generic
            # OSError.  Treat it as an idempotent/conflicting winner only
            # after validating the final entry; otherwise fail closed.
            if path_entry_exists(path):
                return _verify_immutable_bytes(anchor, path, data)
            raise OperationalError(
                f"cannot atomically publish operational file: {path}"
            ) from exc

        try:
            assert_safe_store_path(
                anchor, path, expected="file", allow_missing=False
            )
        except (OSError, UnsafeStorePath) as exc:
            raise OperationalError(f"unsafe operational file: {path}") from exc
        fsync_directory(path.parent)
        return True
    finally:
        # A real process crash can leave an unreferenced temp file, but every
        # ordinary exception path removes it without obscuring the primary
        # publication result/error.
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _write_immutable_temp(parent: Path, basename: str, data: bytes) -> Path:
    """Write and sync one ordinary same-directory publication candidate."""

    try:
        assert_safe_store_path(
            parent, parent, expected="directory", allow_missing=False
        )
    except (OSError, UnsafeStorePath) as exc:
        raise OperationalError(f"unsafe operational directory: {parent}") from exc
    fd, raw_path = tempfile.mkstemp(prefix=f".{basename}.tmp-", dir=parent)
    temp_path = Path(raw_path)
    try:
        assert_safe_store_path(
            parent, temp_path, expected="file", allow_missing=False
        )
        with os.fdopen(fd, "wb", closefd=True) as stream:
            written = stream.write(data)
            if written != len(data):
                raise OSError("short write while staging operational record")
            stream.flush()
            os.fsync(stream.fileno())
        return temp_path
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _verify_immutable_bytes(anchor: Path, path: Path, data: bytes) -> bool:
    """Validate an immutable winner and report an idempotent publication."""

    try:
        assert_safe_store_path(
            anchor, path, expected="file", allow_missing=False
        )
        existing = path.read_bytes()
    except (OSError, UnsafeStorePath) as exc:
        raise OperationalError(f"cannot verify operational file: {path}") from exc
    if existing != data:
        raise IntegrityError(
            f"immutable operational path contains different bytes: {path}"
        )
    return False


def write_immutable_operational(anchor: Path, path: Path, data: bytes) -> bool:
    """Public exact-byte publication helper for machine sidecar services."""

    return _write_immutable(anchor, path, data)


def _read_exact_model(
    anchor: Path, path: Path, model: type[StrictModel]
) -> StrictModel:
    try:
        assert_safe_store_path(
            anchor, path, expected="file", allow_missing=False
        )
        data = path.read_bytes()
        value = model.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise OperationalError(f"invalid operational record: {path}") from exc
    if canonical_json_bytes(value) != data:
        raise IntegrityError(f"operational record is not canonical JSON: {path}")
    return value


@dataclass(frozen=True, slots=True)
class ProjectOperationalLayout:
    project_root: Path
    store_root: Path
    root: Path

    @classmethod
    def at(cls, layout: StoreLayout) -> "ProjectOperationalLayout":
        return cls(
            project_root=layout.project_root,
            store_root=layout.store_root,
            root=layout.store_root / "operational" / "v1",
        )

    @property
    def locks(self) -> Path:
        return self.root / "locks"

    @property
    def operations(self) -> Path:
        return self.root / "operations"

    @property
    def initialization_lock(self) -> Path:
        return self.locks / "initialize"

    @property
    def approvals(self) -> Path:
        return self.root / "approvals"

    @property
    def egress(self) -> Path:
        return self.root / "egress"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def navigation_lock(self) -> Path:
        return self.locks / "navigation"

    @property
    def approval_lock(self) -> Path:
        return self.locks / "approval"

    @property
    def egress_lock(self) -> Path:
        return self.locks / "egress"

    def ensure(self) -> "ProjectOperationalLayout":
        for directory in (
            self.root,
            self.locks,
            self.operations,
            self.approvals,
            self.egress,
            self.runs,
        ):
            _ensure_directory_tree(self.project_root, directory)
        return self


@dataclass(frozen=True, slots=True)
class PreProjectOperationalLayout:
    anchor: Path
    root: Path

    @classmethod
    def for_project(
        cls, project_root: str | Path, *, operational_home: str | Path | None = None
    ) -> "PreProjectOperationalLayout":
        if operational_home is not None:
            home = Path(operational_home).expanduser().absolute()
            anchor = home if home.exists() else home.parent
        elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
            anchor = Path(os.environ["LOCALAPPDATA"]).absolute()
            home = anchor / "EconTheoristAI" / "operational" / "v1"
        else:
            anchor = Path.home().absolute()
            home = anchor / ".local" / "state" / "econ-theorist" / "operational" / "v1"
        if not anchor.is_dir():
            raise OperationalError(
                f"operational-home anchor is unavailable or not a directory: {anchor}"
            )
        binding = sha256_digest(
            str(Path(project_root).expanduser().absolute()).encode("utf-8")
        )
        return cls(anchor=anchor, root=home / "projects" / binding)

    @property
    def locks(self) -> Path:
        return self.root / "locks"

    @property
    def operations(self) -> Path:
        return self.root / "operations"

    @property
    def initialization_lock(self) -> Path:
        return self.locks / "initialize"

    def ensure(self) -> "PreProjectOperationalLayout":
        _ensure_directory_tree(self.anchor, self.operations)
        _ensure_directory_tree(self.anchor, self.locks)
        return self


class ContentAddressedOperationalStore:
    """Immutable content-addressed sidecars beneath one operational root."""

    def __init__(self, anchor: Path, root: Path) -> None:
        self.anchor = anchor
        self.root = root

    def path_for(self, namespace: str, digest: str) -> Path:
        if _KEY_RE.fullmatch(namespace) is None:
            raise OperationalError(f"unsafe operational namespace: {namespace!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise OperationalError(f"invalid content digest: {digest!r}")
        return self.root / namespace / "sha256" / f"{digest}.json"

    def install(self, namespace: str, value: StrictModel | dict[str, Any]) -> tuple[str, Path]:
        data = canonical_json_bytes(value)
        digest = sha256_digest(data)
        path = self.path_for(namespace, digest)
        _write_immutable(self.anchor, path, data)
        return digest, path

    def read_bytes(self, namespace: str, digest: str) -> bytes:
        path = self.path_for(namespace, digest)
        try:
            assert_safe_store_path(
                self.anchor, path, expected="file", allow_missing=False
            )
            data = path.read_bytes()
        except OSError as exc:
            raise OperationalError(
                f"operational content object is unavailable: {namespace}/{digest}"
            ) from exc
        if sha256_digest(data) != digest:
            raise IntegrityError(
                f"operational content object fails digest verification: {path}"
            )
        return data


@dataclass(frozen=True, slots=True)
class OperationState:
    reservation: OperationReservationV1
    response: MachineResponseV1 | None


class OperationJournal:
    """Per-key immutable request/result journal with a hash-linked event log."""

    def __init__(self, *, anchor: Path, operations: Path, locks: Path) -> None:
        self.anchor = anchor
        self.operations = operations
        self.locks = locks

    @classmethod
    def for_project(cls, layout: ProjectOperationalLayout) -> "OperationJournal":
        layout.ensure()
        return cls(anchor=layout.project_root, operations=layout.operations, locks=layout.locks)

    @classmethod
    def for_preproject(cls, layout: PreProjectOperationalLayout) -> "OperationJournal":
        layout.ensure()
        return cls(anchor=layout.anchor, operations=layout.operations, locks=layout.locks)

    def _directory(self, key: str) -> Path:
        return self.operations / _safe_key(key)

    def _lock_path(self, key: str) -> Path:
        digest = sha256_digest(_safe_key(key).encode("utf-8"))
        return self.locks / f"operation-{digest}"

    def _events(self, key: str) -> tuple[tuple[str, LedgerEventV1], ...]:
        root = self._directory(key) / "events"
        if not path_entry_exists(root):
            return ()
        assert_safe_store_path(
            self.anchor, root, expected="directory", allow_missing=False
        )
        result: list[tuple[str, LedgerEventV1]] = []
        previous: str | None = None
        for sequence, path in enumerate(sorted(root.glob("*.json")), start=1):
            loaded = _read_exact_model(self.anchor, path, LedgerEventV1)
            assert isinstance(loaded, LedgerEventV1)
            data = canonical_json_bytes(loaded)
            digest = sha256_digest(data)
            if (
                loaded.ledger_kind != "operation"
                or loaded.subject_id != key
                or loaded.operation_key != key
                or loaded.sequence != sequence
                or loaded.previous_event_hash != previous
                or path.name != f"{sequence:08d}-{digest}.json"
            ):
                raise IntegrityError("operation event chain is inconsistent")
            result.append((digest, loaded))
            previous = digest
        if result:
            kinds = tuple(item.event for _, item in result)
            if kinds not in {("reserved",), ("reserved", "completed")}:
                raise IntegrityError("operation event lifecycle is invalid")
        return tuple(result)

    @contextmanager
    def locked(
        self, key: str, *, timeout: float | None = None
    ) -> Iterator["LockedOperation"]:
        lock_path = self._lock_path(key)
        _ensure_directory_tree(self.anchor, lock_path.parent)
        with ExclusiveFileLock(lock_path, timeout=timeout):
            yield LockedOperation(self, _safe_key(key))

    def inspect(self, key: str) -> OperationState | None:
        directory = self._directory(key)
        reservation_path = directory / "reservation.json"
        if not path_entry_exists(reservation_path):
            return None
        reservation = _read_exact_model(
            self.anchor, reservation_path, OperationReservationV1
        )
        assert isinstance(reservation, OperationReservationV1)
        if reservation.operation_key != key:
            raise IntegrityError("operation reservation names a different key")
        events = self._events(key)
        if events and (
            events[0][1].event != "reserved"
            or events[0][1].request_digest != reservation.request_digest
        ):
            raise IntegrityError("operation reservation event binding is invalid")
        terminal_path = directory / "terminal.json"
        response: MachineResponseV1 | None = None
        if path_entry_exists(terminal_path):
            loaded = _read_exact_model(
                self.anchor, terminal_path, OperationTerminalV1
            )
            assert isinstance(loaded, OperationTerminalV1)
            response = loaded.response
            if (
                loaded.operation_key != reservation.operation_key
                or loaded.operation != reservation.operation
                or loaded.request_digest != reservation.request_digest
                or loaded.response_digest
                != sha256_digest(canonical_json_bytes(response))
                or response.operation != reservation.operation
                or response.request_digest != reservation.request_digest
            ):
                raise IntegrityError(
                    "operation terminal does not bind its reservation/response"
                )
            if len(events) == 2 and (
                events[-1][1].request_digest != reservation.request_digest
                or events[-1][1].payload_hash != loaded.response_digest
            ):
                raise IntegrityError("operation completion event binding is invalid")
        elif len(events) == 2:
            raise IntegrityError("operation completed event lacks its terminal record")
        return OperationState(reservation=reservation, response=response)


class LockedOperation:
    """Operations valid only while the per-key OS lock is held."""

    def __init__(self, journal: OperationJournal, key: str) -> None:
        self.journal = journal
        self.key = key

    @property
    def directory(self) -> Path:
        return self.journal._directory(self.key)

    def _append_event(
        self,
        *,
        event: str,
        request_digest: str | None,
        payload_hash: str | None,
    ) -> str:
        events = self.directory / "events"
        _ensure_directory_tree(self.journal.anchor, events)
        existing = self.journal._events(self.key)
        previous_hash = existing[-1][0] if existing else None
        record = LedgerEventV1(
            ledger_kind="operation",
            subject_id=self.key,
            sequence=len(existing) + 1,
            event=event,
            operation_key=self.key,
            request_digest=request_digest,
            payload_hash=payload_hash,
            previous_event_hash=previous_hash,
            recorded_at=utc_now(),
        )
        data = canonical_json_bytes(record)
        digest = sha256_digest(data)
        path = events / f"{record.sequence:08d}-{digest}.json"
        _write_immutable(self.journal.anchor, path, data)
        return digest

    def _repair_event_projection(self, state: OperationState) -> None:
        events = self.journal._events(self.key)
        if not events:
            self._append_event(
                event="reserved",
                request_digest=state.reservation.request_digest,
                payload_hash=None,
            )
            events = self.journal._events(self.key)
        if state.response is not None and len(events) == 1:
            self._append_event(
                event="completed",
                request_digest=state.reservation.request_digest,
                payload_hash=sha256_digest(
                    canonical_json_bytes(state.response)
                ),
            )

    def reserve(self, request: MachineRequestV1) -> OperationState:
        digest = sha256_digest(canonical_json_bytes(request))
        current = self.journal.inspect(self.key)
        if current is not None:
            if (
                current.reservation.operation != request.operation
                or current.reservation.request_digest != digest
            ):
                raise OperationKeyConflict(
                    "operation key is already bound to different request bytes"
                )
            self._repair_event_projection(current)
            repaired = self.journal.inspect(self.key)
            assert repaired is not None
            return repaired
        reservation = OperationReservationV1(
            operation_key=self.key,
            operation=request.operation,
            request_digest=digest,
            reserved_at=utc_now(),
        )
        _write_immutable(
            self.journal.anchor,
            self.directory / "reservation.json",
            canonical_json_bytes(reservation),
        )
        self._append_event(
            event="reserved", request_digest=digest, payload_hash=None
        )
        return OperationState(reservation=reservation, response=None)

    def complete(self, response: MachineResponseV1) -> OperationState:
        current = self.journal.inspect(self.key)
        if current is None:
            raise OperationalError("operation must be reserved before completion")
        if current.response is not None:
            if current.response != response:
                raise IntegrityError("operation already has a different terminal response")
            self._repair_event_projection(current)
            repaired = self.journal.inspect(self.key)
            assert repaired is not None
            return repaired
        if (
            response.operation != current.reservation.operation
            or response.request_digest != current.reservation.request_digest
        ):
            raise IntegrityError("terminal response differs from its reservation")
        response_data = canonical_json_bytes(response)
        response_digest = sha256_digest(response_data)
        terminal = OperationTerminalV1(
            operation_key=self.key,
            operation=current.reservation.operation,
            request_digest=current.reservation.request_digest,
            response_digest=response_digest,
            response=response,
            completed_at=utc_now(),
        )
        _write_immutable(
            self.journal.anchor,
            self.directory / "terminal.json",
            canonical_json_bytes(terminal),
        )
        self._append_event(
            event="completed",
            request_digest=current.reservation.request_digest,
            payload_hash=response_digest,
        )
        return OperationState(reservation=current.reservation, response=response)


__all__ = [
    "ContentAddressedOperationalStore",
    "LockedOperation",
    "OperationInProgress",
    "OperationJournal",
    "OperationKeyConflict",
    "OperationState",
    "OperationalError",
    "PreProjectOperationalLayout",
    "ProjectOperationalLayout",
    "write_immutable_operational",
]
