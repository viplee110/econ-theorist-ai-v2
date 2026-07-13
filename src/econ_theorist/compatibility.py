"""Strictly read-only project-root and store compatibility recognition.

This module is deliberately below project initialization and canonical replay.
It may inspect filesystem entries and the minimal immutable transaction-chain
metadata needed to choose the current engine, but it never creates a layout,
lock, cache, configuration file, or canonical object.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import stat
from typing import Any, Literal

from . import __version__
from .codec import canonical_json_bytes, transaction_bytes
from .models import CreateEntityOp, Transaction


STORE_DIRECTORY = ".econ-theorist"
CURRENT_TRANSACTION_SCHEMA = 1
MAX_TRANSACTION_BYTES = 64 * 1024 * 1024
MAX_CONFIG_BYTES = 1024 * 1024
MAX_CHAIN_LENGTH = 10_000

CompatibilityClassification = Literal[
    "absent",
    "virgin",
    "valid_existing",
    "recovery_required",
    "corrupt",
    "incompatible",
]

_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_ENGINE_OWNED_EMPTY_DIRS = frozenset(
    {
        "refs",
        "locks",
        "transactions",
        "transactions/sha256",
        "artifacts",
        "artifacts/sha256",
        "provenance",
        "provenance/sha256",
        "runs",
        "snapshots",
        "views",
        "staging",
        "quarantine",
        "quarantine/reports",
    }
)


@dataclass(frozen=True, slots=True)
class CompatibilityProbeResult:
    """One immutable observation from a compatibility probe."""

    classification: CompatibilityClassification
    project_root: str
    store_root: str
    head: str | None = None
    project_id: str | None = None
    transaction_schema: int | None = None
    chain_length: int = 0
    engine_version_hint: str | None = None
    compatible_engine_version: str | None = None
    diagnostics: tuple[str, ...] = ()


class _ProbeFailure(RuntimeError):
    def __init__(self, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.diagnostic = diagnostic


class _Corrupt(_ProbeFailure):
    pass


class _Incompatible(_ProbeFailure):
    def __init__(self, diagnostic: str, *, transaction_schema: int | None = None) -> None:
        super().__init__(diagnostic)
        self.transaction_schema = transaction_schema


class _DuplicateJsonKey(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _StoreInventory:
    directories: frozenset[str]
    files: frozenset[str]


def _absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(Path(path).expanduser())))


def _entry_stat(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _Corrupt(f"path_metadata_unavailable:{path}") from exc


def _is_reparse(metadata: os.stat_result) -> bool:
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _require_ordinary_directory(path: Path, *, label: str) -> None:
    metadata = _entry_stat(path)
    if metadata is None:
        raise _Corrupt(f"{label}_missing")
    if _is_reparse(metadata):
        raise _Corrupt(f"{label}_reparse")
    if not stat.S_ISDIR(metadata.st_mode):
        raise _Corrupt(f"{label}_not_directory")


def _directory_entries(path: Path) -> list[os.DirEntry[str]]:
    try:
        with os.scandir(path) as iterator:
            return list(iterator)
    except OSError as exc:
        raise _Corrupt(f"directory_scan_failed:{path}") from exc


def _scan_for_nested_stores(project_root: Path, primary_store: Path) -> None:
    """Reject another store below the exact selected project root.

    Unrelated filesystem links are not followed. A link or reparse point named
    ``.econ-theorist`` is itself rejected as a nested-store boundary attack.
    The primary store is inventoried separately, including any store nested
    inside it.
    """

    pending = [project_root]
    while pending:
        directory = pending.pop()
        for entry in _directory_entries(directory):
            path = Path(entry.path)
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise _Corrupt(f"path_metadata_unavailable:{path}") from exc
            if entry.name == STORE_DIRECTORY:
                if path == primary_store:
                    continue
                raise _Corrupt(f"nested_store:{path}")
            if _is_reparse(metadata):
                continue
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(path)


def _inventory_store(store_root: Path) -> _StoreInventory:
    directories: set[str] = set()
    files: set[str] = set()
    pending = [store_root]
    while pending:
        directory = pending.pop()
        for entry in _directory_entries(directory):
            path = Path(entry.path)
            relative = path.relative_to(store_root).as_posix()
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise _Corrupt(f"path_metadata_unavailable:{relative}") from exc
            if _is_reparse(metadata):
                raise _Corrupt(f"store_entry_reparse:{relative}")
            if stat.S_ISDIR(metadata.st_mode):
                if entry.name == STORE_DIRECTORY:
                    raise _Corrupt(f"nested_store:{relative}")
                directories.add(relative)
                pending.append(path)
            elif stat.S_ISREG(metadata.st_mode):
                files.add(relative)
            else:
                raise _Corrupt(f"store_entry_not_regular:{relative}")
    return _StoreInventory(frozenset(directories), frozenset(files))


def _read_regular_file(path: Path, *, store_root: Path, maximum: int) -> bytes:
    try:
        path.relative_to(store_root)
    except ValueError as exc:
        raise _Corrupt(f"store_read_escape:{path}") from exc

    metadata = _entry_stat(path)
    if metadata is None:
        raise _Corrupt(f"required_file_missing:{path.relative_to(store_root).as_posix()}")
    if _is_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise _Corrupt(f"required_file_not_regular:{path.relative_to(store_root).as_posix()}")
    if metadata.st_size > maximum:
        raise _Corrupt(f"required_file_too_large:{path.relative_to(store_root).as_posix()}")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        relative = path.relative_to(store_root).as_posix()
        raise _Corrupt(f"required_file_unreadable:{relative}") from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > maximum:
            raise _Corrupt(
                f"required_file_changed:{path.relative_to(store_root).as_posix()}"
            )
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise _Corrupt(
                    f"required_file_short_read:{path.relative_to(store_root).as_posix()}"
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    finally:
        os.close(descriptor)

    after = _entry_stat(path)
    if after is None or _is_reparse(after) or not stat.S_ISREG(after.st_mode):
        raise _Corrupt(f"required_file_changed:{path.relative_to(store_root).as_posix()}")
    before_identity = (getattr(opened, "st_dev", 0), getattr(opened, "st_ino", 0))
    after_identity = (getattr(after, "st_dev", 0), getattr(after, "st_ino", 0))
    if before_identity != after_identity and all(before_identity) and all(after_identity):
        raise _Corrupt(f"required_file_changed:{path.relative_to(store_root).as_posix()}")
    return data


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(key)
        result[key] = value
    return result


def _decode_canonical_json(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        decoded = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _Corrupt(f"{label}_invalid_json") from exc
    if not isinstance(decoded, dict):
        raise _Corrupt(f"{label}_not_object")
    try:
        canonical = canonical_json_bytes(decoded)
    except (TypeError, ValueError) as exc:
        raise _Corrupt(f"{label}_noncanonical") from exc
    if canonical != data:
        raise _Corrupt(f"{label}_noncanonical")
    return decoded


def _read_transaction(
    store_root: Path, digest: str
) -> tuple[Transaction, int]:
    path = store_root / "transactions" / "sha256" / digest
    data = _read_regular_file(path, store_root=store_root, maximum=MAX_TRANSACTION_BYTES)
    if hashlib.sha256(data).hexdigest() != digest:
        raise _Corrupt(f"transaction_digest_mismatch:{digest}")
    decoded = _decode_canonical_json(data, label=f"transaction:{digest}")
    schema = decoded.get("transaction_schema")
    if not isinstance(schema, int) or isinstance(schema, bool):
        raise _Corrupt(f"transaction_schema_invalid:{digest}")
    if schema != CURRENT_TRANSACTION_SCHEMA:
        raise _Incompatible(
            f"transaction_schema_unsupported:{schema}", transaction_schema=schema
        )
    try:
        transaction = Transaction.model_validate_json(data, strict=True)
    except ValueError as exc:
        raise _Corrupt(f"transaction_schema_inconsistent:{digest}") from exc
    if transaction_bytes(transaction) != data:
        raise _Corrupt(f"transaction_bytes_noncanonical:{digest}")
    return transaction, schema


def _inspect_chain(
    store_root: Path, head: str
) -> tuple[str, int, int]:
    cursor: str | None = head
    seen: set[str] = set()
    project_id: str | None = None
    schema = CURRENT_TRANSACTION_SCHEMA
    length = 0
    while cursor is not None:
        if cursor in seen:
            raise _Corrupt("transaction_chain_cycle")
        if length >= MAX_CHAIN_LENGTH:
            raise _Corrupt("transaction_chain_too_long")
        seen.add(cursor)
        transaction, schema = _read_transaction(store_root, cursor)
        length += 1
        if project_id is None:
            project_id = transaction.project_id
        elif transaction.project_id != project_id:
            raise _Corrupt("transaction_project_identity_mismatch")

        parent = transaction.parent_transaction_hash
        if parent is None:
            if transaction.origin != "genesis":
                raise _Corrupt("transaction_chain_missing_genesis")
            project_creations = [
                operation.entity
                for operation in transaction.operations
                if isinstance(operation, CreateEntityOp)
                and operation.entity.entity_type == "Project"
                and operation.entity.entity_id == transaction.project_id
                and operation.entity.project_id == transaction.project_id
            ]
            if len(project_creations) != 1:
                raise _Corrupt("genesis_project_identity_invalid")
        elif transaction.origin == "genesis":
            raise _Corrupt("transaction_chain_repeated_genesis")
        cursor = parent

    if project_id is None:
        raise _Corrupt("transaction_chain_empty")
    return project_id, schema, length


def _config_hints(
    store_root: Path,
    inventory: _StoreInventory,
    canonical_project_id: str,
) -> tuple[str | None, tuple[str, ...]]:
    if "project.json" in inventory.directories:
        return None, ("project_config_invalid",)
    if "project.json" not in inventory.files:
        return None, ("project_config_missing",)
    path = store_root / "project.json"
    try:
        data = _read_regular_file(path, store_root=store_root, maximum=MAX_CONFIG_BYTES)
        decoded = json.loads(
            data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (_ProbeFailure, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None, ("project_config_invalid",)
    if not isinstance(decoded, dict):
        return None, ("project_config_invalid",)
    diagnostics: list[str] = []
    configured_project = decoded.get("project_id")
    if configured_project != canonical_project_id:
        diagnostics.append("project_config_project_id_mismatch")
    engine_hint = decoded.get("engine_version")
    if not isinstance(engine_hint, str) or not engine_hint:
        engine_hint = None
        diagnostics.append("project_config_engine_version_missing")
    return engine_hint, tuple(diagnostics)


def _result(
    classification: CompatibilityClassification,
    project_root: Path,
    store_root: Path,
    **values: Any,
) -> CompatibilityProbeResult:
    return CompatibilityProbeResult(
        classification=classification,
        project_root=str(project_root),
        store_root=str(store_root),
        **values,
    )


def probe_project_root(
    project_root: str | Path,
    *,
    expected_project_id: str | None = None,
) -> CompatibilityProbeResult:
    """Classify one exact project root without changing any filesystem state.

    ``valid_existing`` means that the current engine can safely parse the exact
    content-addressed transaction chain and recover its canonical project
    identity. Full semantic replay and generated-config repair intentionally
    occur only after this probe has selected a compatible engine.
    """

    root = _absolute(project_root)
    store = root / STORE_DIRECTORY
    try:
        root_metadata = _entry_stat(root)
        if root_metadata is None:
            return _result("absent", root, store, diagnostics=("project_root_absent",))
        if _is_reparse(root_metadata):
            raise _Corrupt("project_root_reparse")
        if not stat.S_ISDIR(root_metadata.st_mode):
            raise _Corrupt("project_root_not_directory")
        if root.name == STORE_DIRECTORY:
            raise _Corrupt("selected_root_is_store")

        store_metadata = _entry_stat(store)
        if store_metadata is not None:
            if _is_reparse(store_metadata):
                raise _Corrupt("store_root_reparse")
            if not stat.S_ISDIR(store_metadata.st_mode):
                raise _Corrupt("store_root_not_directory")
        _scan_for_nested_stores(root, store)
        if store_metadata is None:
            return _result("absent", root, store, diagnostics=("store_absent",))

        _require_ordinary_directory(store, label="store_root")
        inventory = _inventory_store(store)
        if not inventory.files and inventory.directories.issubset(
            _ENGINE_OWNED_EMPTY_DIRS
        ):
            return _result("virgin", root, store, diagnostics=("store_virgin",))

        if "refs/main" in inventory.directories:
            raise _Corrupt("head_not_regular")
        if "refs/main" not in inventory.files:
            return _result(
                "recovery_required",
                root,
                store,
                diagnostics=("headless_store_residue",),
            )
        extra_refs = sorted(
            path for path in inventory.files if path.startswith("refs/") and path != "refs/main"
        )
        if extra_refs:
            return _result(
                "recovery_required",
                root,
                store,
                diagnostics=("unexpected_ref_entries",),
            )
        head_bytes = _read_regular_file(
            store / "refs" / "main", store_root=store, maximum=64
        )
        try:
            head = head_bytes.decode("ascii")
        except UnicodeDecodeError as exc:
            raise _Corrupt("head_invalid") from exc
        if _DIGEST_PATTERN.fullmatch(head) is None:
            raise _Corrupt("head_invalid")

        project_id, transaction_schema, chain_length = _inspect_chain(store, head)
        if expected_project_id is not None and expected_project_id != project_id:
            raise _Corrupt("selected_project_identity_mismatch")
        engine_hint, config_diagnostics = _config_hints(
            store, inventory, project_id
        )
        return _result(
            "valid_existing",
            root,
            store,
            head=head,
            project_id=project_id,
            transaction_schema=transaction_schema,
            chain_length=chain_length,
            engine_version_hint=engine_hint,
            compatible_engine_version=__version__,
            diagnostics=(*config_diagnostics, "full_semantic_validation_required"),
        )
    except _Incompatible as exc:
        return _result(
            "incompatible",
            root,
            store,
            transaction_schema=exc.transaction_schema,
            diagnostics=(exc.diagnostic,),
        )
    except _Corrupt as exc:
        return _result(
            "corrupt", root, store, diagnostics=(exc.diagnostic,)
        )


probe_compatibility = probe_project_root


__all__ = [
    "CompatibilityClassification",
    "CompatibilityProbeResult",
    "probe_compatibility",
    "probe_project_root",
]
