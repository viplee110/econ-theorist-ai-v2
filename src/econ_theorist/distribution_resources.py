"""Locate data-file resources owned by an installed distribution."""

from __future__ import annotations

from functools import lru_cache
import importlib.metadata
from pathlib import Path, PurePosixPath


class DistributionResourceError(RuntimeError):
    """An installed distribution cannot prove one unambiguous resource root."""


_DISTRIBUTION_NAME = "econ-theorist-ai"
_SHARE_ROOT_PARTS = ("share", "econ-theorist")


def _record_parts(entry: object) -> tuple[str, ...]:
    """Normalize one RECORD entry without interpreting host separators."""

    raw = str(entry).replace("\\", "/")
    return PurePosixPath(raw).parts


@lru_cache(maxsize=1)
def installed_resource_root() -> Path:
    """Return the installed ``<environment>/share/econ-theorist`` directory.

    ``Distribution.locate_file("share/...")`` is not portable for wheel
    ``data_files``: after installation, their RECORD entries commonly begin
    with ``../../..`` from ``site-packages``.  The RECORD-backed
    ``Distribution.files`` entries are authoritative.  Locate one of those
    exact entries first, then derive and cross-check the common share root.
    """

    try:
        dist = importlib.metadata.distribution(_DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError as exc:
        raise DistributionResourceError(
            f"installed distribution is unavailable: {_DISTRIBUTION_NAME}"
        ) from exc

    entries = dist.files
    if not entries:
        raise DistributionResourceError(
            "installed distribution has no RECORD resource inventory"
        )

    candidates: set[Path] = set()
    matched_entries = 0
    for entry in entries:
        parts = _record_parts(entry)
        matches = tuple(
            index
            for index in range(len(parts) - len(_SHARE_ROOT_PARTS) + 1)
            if parts[index : index + len(_SHARE_ROOT_PARTS)] == _SHARE_ROOT_PARTS
            and all(part == ".." for part in parts[:index])
        )
        if not matches:
            continue
        if len(matches) != 1:
            raise DistributionResourceError(
                "installed resource RECORD entry has an ambiguous share root"
            )
        index = matches[0]
        tail = parts[index + len(_SHARE_ROOT_PARTS) :]
        if not tail:
            continue
        if any(part in {".", ".."} for part in tail):
            raise DistributionResourceError(
                "installed resource RECORD entry escapes its share root"
            )

        try:
            located = Path(dist.locate_file(entry)).resolve(strict=False)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise DistributionResourceError(
                "installed resource RECORD entry cannot be located"
            ) from exc
        if not located.is_file():
            raise DistributionResourceError(
                f"inventoried installed resource is missing: {located}"
            )
        root = located
        for _ in tail:
            root = root.parent
        candidates.add(root)
        matched_entries += 1

    if matched_entries == 0:
        raise DistributionResourceError(
            "installed distribution does not inventory share/econ-theorist resources"
        )
    if len(candidates) != 1:
        raise DistributionResourceError(
            "installed distribution inventories multiple share/econ-theorist roots"
        )
    root = next(iter(candidates))
    if not root.is_dir():
        raise DistributionResourceError(
            f"installed resource root is missing: {root}"
        )
    return root


__all__ = ["DistributionResourceError", "installed_resource_root"]
