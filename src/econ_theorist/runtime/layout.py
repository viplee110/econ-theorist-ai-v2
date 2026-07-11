"""Portable on-disk layout for the Phase 1 runtime.

The layout object only creates directories.  It deliberately does not create
``project.json`` or ``refs/main``: those files become meaningful only when the
initialization/commit layers can write valid canonical content.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


STORE_DIRECTORY = ".econ-theorist"


class UnsafeStorePath(RuntimeError):
    """A runtime path crosses or names an unsafe filesystem object."""


def _absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(Path(path).expanduser())))


def _entry_stat(path: Path) -> os.stat_result | None:
    """Return an entry's own metadata, including dangling links."""

    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _is_reparse(stat_result: os.stat_result) -> bool:
    """Recognize POSIX links and Windows symlinks/junctions/reparse points."""

    if stat.S_ISLNK(stat_result.st_mode):
        return True
    attributes = getattr(stat_result, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def path_entry_exists(path: str | Path) -> bool:
    """Like ``lexists``: dangling links and other directory entries count."""

    return _entry_stat(Path(path)) is not None


def assert_safe_store_path(
    root: str | Path,
    candidate: str | Path,
    *,
    expected: str | None = None,
    allow_missing: bool = True,
) -> Path:
    """Validate one lexical descendant without following indirections.

    Every existing component from ``root`` through ``candidate`` must be an
    ordinary directory, except that the final component may be an ordinary
    file when ``expected='file'``.  Symlinks, Windows junctions, and all other
    reparse points are rejected even if they resolve back inside the store.
    """

    if expected not in {None, "directory", "file"}:
        raise ValueError("expected must be 'directory', 'file', or None")
    root_path = _absolute(root)
    candidate_path = _absolute(candidate)
    try:
        relative = candidate_path.relative_to(root_path)
    except ValueError as exc:
        raise UnsafeStorePath(
            f"runtime path escapes its lexical root: {candidate_path}"
        ) from exc

    descendants = tuple(
        root_path / Path(*relative.parts[:index])
        for index in range(1, len(relative.parts) + 1)
    )
    components = (root_path, *descendants)
    for index, component in enumerate(components):
        metadata = _entry_stat(component)
        is_final = index == len(components) - 1
        if metadata is None:
            if is_final and not allow_missing:
                raise FileNotFoundError(component)
            # Once a parent is absent, a deeper ordinary entry cannot exist.
            continue
        if _is_reparse(metadata):
            raise UnsafeStorePath(
                f"runtime paths cannot contain symlinks, junctions, or "
                f"reparse points: {component}"
            )
        required_kind = expected if is_final else "directory"
        if required_kind == "file" and not stat.S_ISREG(metadata.st_mode):
            raise UnsafeStorePath(f"runtime file is not ordinary: {component}")
        if required_kind != "file" and not stat.S_ISDIR(metadata.st_mode):
            raise UnsafeStorePath(
                f"runtime directory component is not ordinary: {component}"
            )

    # The lexical check above is authoritative.  This second check detects
    # platform indirections that resolve() knows about even if lstat metadata
    # is incomplete on a particular Python/Windows combination.
    resolved_root = root_path.resolve(strict=False)
    resolved_candidate = candidate_path.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise UnsafeStorePath(
            f"runtime path resolves outside its root: {candidate_path}"
        ) from exc
    return candidate_path


@dataclass(frozen=True, slots=True)
class StoreLayout:
    """All machine-local paths used by one project runtime.

    Logical references stored in canonical objects must remain relative; this
    class is the one place where they are anchored to a machine path.
    """

    project_root: Path
    store_root: Path

    STORE_DIRECTORY: ClassVar[str] = STORE_DIRECTORY

    @classmethod
    def at(cls, project_root: str | Path) -> "StoreLayout":
        """Build a layout rooted at ``project_root`` without touching disk."""

        root = _absolute(project_root)
        return cls(project_root=root, store_root=root / STORE_DIRECTORY)

    @classmethod
    def from_store_root(cls, store_root: str | Path) -> "StoreLayout":
        """Build a layout when the ``.econ-theorist`` path is already known."""

        store = _absolute(store_root)
        if store.name != STORE_DIRECTORY:
            raise ValueError(
                f"store root must be named {STORE_DIRECTORY!r}, got {store.name!r}"
            )
        return cls(project_root=store.parent, store_root=store)

    @property
    def project_file(self) -> Path:
        return self.store_root / "project.json"

    @property
    def refs_dir(self) -> Path:
        return self.store_root / "refs"

    @property
    def main_ref(self) -> Path:
        return self.refs_dir / "main"

    @property
    def locks_dir(self) -> Path:
        return self.store_root / "locks"

    @property
    def commit_lock(self) -> Path:
        return self.locks_dir / "commit"

    @property
    def transactions_dir(self) -> Path:
        return self.store_root / "transactions"

    @property
    def transactions_root(self) -> Path:
        return self.transactions_dir / "sha256"

    @property
    def artifacts_dir(self) -> Path:
        return self.store_root / "artifacts"

    @property
    def artifacts_root(self) -> Path:
        return self.artifacts_dir / "sha256"

    @property
    def provenance_dir(self) -> Path:
        return self.store_root / "provenance"

    @property
    def provenance_root(self) -> Path:
        return self.provenance_dir / "sha256"

    @property
    def runs_dir(self) -> Path:
        return self.store_root / "runs"

    @property
    def snapshots_dir(self) -> Path:
        return self.store_root / "snapshots"

    @property
    def latest_snapshot(self) -> Path:
        return self.snapshots_dir / "latest.json"

    @property
    def views_dir(self) -> Path:
        return self.store_root / "views"

    @property
    def status_view(self) -> Path:
        return self.views_dir / "status.md"

    @property
    def staging_dir(self) -> Path:
        return self.store_root / "staging"

    @property
    def quarantine_dir(self) -> Path:
        return self.store_root / "quarantine"

    @property
    def quarantine_reports_dir(self) -> Path:
        return self.quarantine_dir / "reports"

    @property
    def required_directories(self) -> tuple[Path, ...]:
        """Directories whose existence is safe and idempotent to establish."""

        return (
            self.store_root,
            self.refs_dir,
            self.locks_dir,
            self.transactions_dir,
            self.transactions_root,
            self.artifacts_dir,
            self.artifacts_root,
            self.provenance_dir,
            self.provenance_root,
            self.runs_dir,
            self.snapshots_dir,
            self.views_dir,
            self.staging_dir,
            self.quarantine_dir,
            self.quarantine_reports_dir,
        )

    def ensure(self) -> "StoreLayout":
        """Create the directory skeleton and return ``self``.

        A regular file at any required directory path is rejected rather than
        replaced.  Existing project content is never modified here.
        """

        if path_entry_exists(self.project_root):
            assert_safe_store_path(
                self.project_root,
                self.project_root,
                expected="directory",
                allow_missing=False,
            )
        else:
            self.project_root.mkdir(parents=True, exist_ok=False)
            assert_safe_store_path(
                self.project_root,
                self.project_root,
                expected="directory",
                allow_missing=False,
            )
        for directory in self.required_directories:
            assert_safe_store_path(
                self.project_root,
                directory,
                expected="directory",
                allow_missing=True,
            )
            if not path_entry_exists(directory):
                # required_directories is deliberately parent-before-child;
                # never ask mkdir(parents=True) to cross an unchecked entry.
                directory.mkdir(exist_ok=False)
            assert_safe_store_path(
                self.project_root,
                directory,
                expected="directory",
                allow_missing=False,
            )
        return self


def initialize_layout(project_root: str | Path) -> StoreLayout:
    """Create and return the Phase 1 store skeleton for a project."""

    return StoreLayout.at(project_root).ensure()
