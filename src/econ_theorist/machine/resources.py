"""Pinned, packaged policy resources owned by the Phase 5A facade."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from ..codec import canonical_json_bytes, sha256_digest
from ..distribution_resources import (
    DistributionResourceError,
    installed_resource_root,
)
from ..errors import RegistryError
from ..models import Digest, StrictModel
from ..policy import ROUTE_REGISTRY_V4_HASH
from ..route_registry import load_registry


NAVIGATION_REGISTRY_V1_HASH = (
    "b1f9920afe21ee22c863592c072e5e79ebdcef9975961c96dcd6a5b7508a8aaf"
)
HOST_MANIFEST_V1_HASH = (
    "f9e254ddd20f01d765f9d056d18610796bb33ba07aaa2d971fe87b44dc0bd57a"
)
COMPATIBILITY_SUPPORT_V1_HASH = (
    "1d7743fd4eb22b7ec435aa532125aa77aa3080c6a90fccb3feb3fb0f0aa2d38a"
)


class NavigationRoutePolicyV1(StrictModel):
    route_id: str
    route_version: Annotated[int, Field(ge=1)]
    selector_id: Literal[
        "empty_focus.v1", "registry_cardinality.v1", "stale_current_typed_root.v1"
    ]
    prerequisite_probe_id: Literal[
        "entry_validator_diagnostics.v1", "stale_dependency_probe.v1"
    ]
    entry_validator_id: str
    purpose: str
    default_budget_units: Annotated[int, Field(ge=1)]


class NavigationRegistryV1(StrictModel):
    navigation_registry_schema: Literal[1]
    navigation_registry_version: Literal[1]
    route_registry_hash: Digest
    max_candidate_sets: Annotated[int, Field(ge=1)]
    routes: tuple[NavigationRoutePolicyV1, ...]


def _machine_resource_root() -> Path:
    source_root = Path(__file__).resolve().parents[3] / "machine"
    if (source_root / "navigation-registry.v1.json").is_file():
        return source_root
    try:
        installed_root = installed_resource_root() / "machine"
    except DistributionResourceError as exc:
        raise RegistryError("cannot locate machine policy resources") from exc
    if not installed_root.is_dir():
        raise RegistryError(
            f"installed machine policy resources are missing: {installed_root}"
        )
    return installed_root


def _load_json_resource(filename: str, expected_hash: str) -> dict[str, object]:
    path = _machine_resource_root() / filename
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"invalid machine policy resource: {path}") from exc
    if not isinstance(value, dict):
        raise RegistryError(f"machine policy resource is not an object: {path}")
    actual = sha256_digest(canonical_json_bytes(value))
    if actual != expected_hash:
        raise RegistryError(
            f"machine policy resource differs from pinned hash: {filename}"
        )
    return value


@lru_cache(maxsize=1)
def load_navigation_registry() -> NavigationRegistryV1:
    raw = _load_json_resource(
        "navigation-registry.v1.json", NAVIGATION_REGISTRY_V1_HASH
    )
    try:
        registry = NavigationRegistryV1.model_validate_json(
            canonical_json_bytes(raw), strict=True
        )
    except ValueError as exc:
        raise RegistryError("invalid navigation registry v1") from exc
    active = load_registry()
    if registry.route_registry_hash != ROUTE_REGISTRY_V4_HASH:
        raise RegistryError("navigation registry is bound to the wrong route registry")
    expected = tuple(
        (
            route.route_id,
            route.route_version,
            route.entry_validator_id,
            route.allowed_purposes,
        )
        for route in active.routes
        if route.availability == "enabled"
    )
    actual = tuple(
        (
            item.route_id,
            item.route_version,
            item.entry_validator_id,
            (item.purpose,),
        )
        for item in registry.routes
    )
    if actual != expected:
        raise RegistryError(
            "navigation registry does not exactly cover the active enabled routes"
        )
    return registry


@lru_cache(maxsize=1)
def load_host_manifest() -> dict[str, object]:
    return _load_json_resource("host-manifest.v1.json", HOST_MANIFEST_V1_HASH)


@lru_cache(maxsize=1)
def load_compatibility_support() -> dict[str, object]:
    return _load_json_resource(
        "compatibility-support.v1.json", COMPATIBILITY_SUPPORT_V1_HASH
    )


def machine_resource_path(filename: str) -> Path:
    """Return a verified resource path for inventory construction."""

    expected = {
        "navigation-registry.v1.json": NAVIGATION_REGISTRY_V1_HASH,
        "host-manifest.v1.json": HOST_MANIFEST_V1_HASH,
        "compatibility-support.v1.json": COMPATIBILITY_SUPPORT_V1_HASH,
    }.get(filename)
    if expected is None:
        raise RegistryError(f"unknown machine resource: {filename}")
    _load_json_resource(filename, expected)
    return _machine_resource_root() / filename


__all__ = [
    "COMPATIBILITY_SUPPORT_V1_HASH",
    "HOST_MANIFEST_V1_HASH",
    "NAVIGATION_REGISTRY_V1_HASH",
    "NavigationRegistryV1",
    "NavigationRoutePolicyV1",
    "load_compatibility_support",
    "load_host_manifest",
    "load_navigation_registry",
    "machine_resource_path",
]
