"""Portable capability discovery with explicit impact and soft degradation."""

from __future__ import annotations

import importlib.metadata
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from .policy import (
    PINNED_PYDANTIC_CORE_VERSION,
    PINNED_PYDANTIC_VERSION,
    load_route_registry,
    registry_hash,
)
from .runtime import HeadStore, StoreLayout


OPTIONAL_TOOLS: tuple[tuple[str, str, str], ...] = (
    ("git", "git", "optional file-level checkpoints and diffs"),
    ("latexmk", "latexmk", "optional LaTeX compilation"),
    ("pdflatex", "pdflatex", "optional direct LaTeX compilation"),
    ("wolframscript", "wolframscript", "optional symbolic verification adapter"),
    ("lean", "lean", "optional formal-proof adapter"),
    ("node", "node", "optional JavaScript-based adapters"),
)


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def doctor_report(project_root: str | Path | None = None) -> dict[str, Any]:
    """Return machine-readable capabilities without installing or mutating anything."""

    python_ok = sys.version_info >= (3, 11)
    pydantic_version = _package_version("pydantic")
    pydantic_core_version = _package_version("pydantic-core")
    validator_ok = (
        pydantic_version == PINNED_PYDANTIC_VERSION
        and pydantic_core_version == PINNED_PYDANTIC_CORE_VERSION
    )
    checks: list[dict[str, Any]] = [
        {
            "capability": "python_runtime",
            "available": python_ok,
            "required": True,
            "version": platform.python_version(),
            "impact": "the local runtime cannot execute" if not python_ok else "ready",
        },
        {
            "capability": "pydantic_models",
            "available": validator_ok,
            "required": True,
            "version": (
                f"pydantic {pydantic_version}; pydantic-core {pydantic_core_version}"
            ),
            "impact": (
                "canonical validator is missing or differs from the pinned versions"
                if not validator_ok
                else "ready"
            ),
        },
    ]

    try:
        registry = load_route_registry()
        registry_ok = True
        enabled = sum(route.availability == "enabled" for route in registry.routes)
        registry_detail = (
            f"active v{registry.registry_version}; {len(registry.routes)} routes; "
            f"{enabled} enabled; sha256:{registry_hash(registry)}"
        )
    except Exception as exc:  # report diagnostics; callers decide whether to fail
        registry_ok = False
        registry_detail = f"{type(exc).__name__}: {exc}"
    checks.append(
        {
            "capability": "route_registry",
            "available": registry_ok,
            "required": True,
            "version": registry_detail,
            "impact": "runs cannot begin" if not registry_ok else "ready",
        }
    )

    for capability, executable, impact in OPTIONAL_TOOLS:
        path = shutil.which(executable)
        checks.append(
            {
                "capability": capability,
                "available": path is not None,
                "required": False,
                "version": None,
                "impact": "ready" if path else f"{impact} unavailable; theory core continues",
            }
        )

    if project_root is not None:
        layout = StoreLayout.at(project_root)
        initialized = layout.project_file.is_file() and layout.main_ref.is_file()
        head: str | None = None
        head_error: str | None = None
        if initialized:
            try:
                head = HeadStore(layout).read()
            except Exception as exc:
                head_error = f"{type(exc).__name__}: {exc}"
        checks.append(
            {
                "capability": "project_store",
                "available": initialized and head is not None and head_error is None,
                "required": False,
                "version": head,
                "impact": (
                    head_error
                    or ("ready" if initialized else "run etai init before project routes")
                ),
            }
        )

    required_ok = all(check["available"] for check in checks if check["required"])
    return {
        "schema": "econ-theorist/doctor/v1",
        "required_ok": required_ok,
        "checks": checks,
    }
