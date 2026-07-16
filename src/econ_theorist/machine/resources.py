"""Pinned, packaged policy resources owned by the Phase 5A facade."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from ..codec import canonical_json_bytes, sha256_digest
from ..distribution_resources import (
    DistributionResourceError,
    installed_resource_root,
)
from ..errors import RegistryError
from ..models import Digest, StrictModel
from ..policy import (
    ROUTE_REGISTRY_V4_HASH,
    ROUTE_REGISTRY_V5_HASH,
    ROUTE_REGISTRY_V6_HASH,
    ROUTE_REGISTRY_V7_HASH,
    ROUTE_REGISTRY_V8_HASH,
    load_route_registry_by_hash,
)


NAVIGATION_REGISTRY_V1_HASH = (
    "b1f9920afe21ee22c863592c072e5e79ebdcef9975961c96dcd6a5b7508a8aaf"
)
NAVIGATION_REGISTRY_V2_HASH = (
    "262140bc73fb2b0a14c0d7ea884b36d07997aae4c63403f9091bb28ad2fccf81"
)
NAVIGATION_REGISTRY_V3_HASH = (
    "fe285a46a1da5e1dd0f9c2953d0c6a6cf7474ff39129d53c5be96548548bf594"
)
NAVIGATION_REGISTRY_V4_HASH = (
    "4027c38ffbc43af55f2c8fc1fd6bdf634024e9b7a3cc1e88b426c20556634833"
)
NAVIGATION_REGISTRY_V5_HASH = (
    "50b3943aa43aa989e33a27bef48eb6de66e41cf8048ff856fa2183397caa9a4c"
)
NAVIGATION_REGISTRY_V6_HASH = (
    "94520d9626e702fde479be0184bbc5baa3cc25dce9c8f65e1d935064923f826f"
)
NAVIGATION_REGISTRY_V7_HASH = (
    "ea133669cd85c073b6352744f2d1b5413dfe33d738752ad17769637acfd9e510"
)
NAVIGATION_REGISTRY_HASH = NAVIGATION_REGISTRY_V7_HASH
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
        "empty_focus.v1",
        "framing_or_stale_repair_root.v1",
        "registry_cardinality.v1",
        "stale_current_typed_root.v1",
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


class NavigationRegistryV2(StrictModel):
    navigation_registry_schema: Literal[1]
    navigation_registry_version: Literal[2]
    route_registry_hash: Digest
    max_candidate_sets: Annotated[int, Field(ge=1)]
    routes: tuple[NavigationRoutePolicyV1, ...]


class NavigationRoutePolicyV3(NavigationRoutePolicyV1):
    selector_id: Literal[
        "empty_focus.v1",
        "framing_or_stale_repair_root.v1",
        "registry_cardinality.v1",
        "stale_current_typed_root.v1",
        "uncompleted_decomposition_scope.v1",
    ]


class NavigationRegistryV3(StrictModel):
    navigation_registry_schema: Literal[1]
    navigation_registry_version: Literal[3]
    route_registry_hash: Digest
    max_candidate_sets: Annotated[int, Field(ge=1)]
    routes: tuple[NavigationRoutePolicyV3, ...]


class NavigationRegistryV4(StrictModel):
    navigation_registry_schema: Literal[1]
    navigation_registry_version: Literal[4]
    route_registry_hash: Digest
    max_candidate_sets: Annotated[int, Field(ge=1)]
    routes: tuple[NavigationRoutePolicyV3, ...]


class NavigationRegistryV5(StrictModel):
    navigation_registry_schema: Literal[1]
    navigation_registry_version: Literal[5]
    route_registry_hash: Digest
    max_candidate_sets: Annotated[int, Field(ge=1)]
    routes: tuple[NavigationRoutePolicyV3, ...]


class NavigationRegistryV6(StrictModel):
    navigation_registry_schema: Literal[1]
    navigation_registry_version: Literal[6]
    route_registry_hash: Digest
    max_candidate_sets: Annotated[int, Field(ge=1)]
    routes: tuple[NavigationRoutePolicyV3, ...]


class NavigationRegistryV7(StrictModel):
    navigation_registry_schema: Literal[1]
    navigation_registry_version: Literal[7]
    route_registry_hash: Digest
    max_candidate_sets: Annotated[int, Field(ge=1)]
    routes: tuple[NavigationRoutePolicyV3, ...]


NavigationRegistryLike: TypeAlias = (
    NavigationRegistryV1
    | NavigationRegistryV2
    | NavigationRegistryV3
    | NavigationRegistryV4
    | NavigationRegistryV5
    | NavigationRegistryV6
    | NavigationRegistryV7
)


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


def _load_navigation_registry_resource(
    filename: str, expected_hash: str
) -> NavigationRegistryLike:
    raw = _load_json_resource(filename, expected_hash)
    version = raw.get("navigation_registry_version")
    try:
        if version == 1:
            registry: NavigationRegistryLike = NavigationRegistryV1.model_validate_json(
                canonical_json_bytes(raw), strict=True
            )
            expected_route_registry_hash = ROUTE_REGISTRY_V4_HASH
        elif version == 2:
            registry = NavigationRegistryV2.model_validate_json(
                canonical_json_bytes(raw), strict=True
            )
            expected_route_registry_hash = ROUTE_REGISTRY_V5_HASH
        elif version == 3:
            registry = NavigationRegistryV3.model_validate_json(
                canonical_json_bytes(raw), strict=True
            )
            expected_route_registry_hash = ROUTE_REGISTRY_V5_HASH
        elif version == 4:
            registry = NavigationRegistryV4.model_validate_json(
                canonical_json_bytes(raw), strict=True
            )
            expected_route_registry_hash = ROUTE_REGISTRY_V5_HASH
        elif version == 5:
            registry = NavigationRegistryV5.model_validate_json(
                canonical_json_bytes(raw), strict=True
            )
            expected_route_registry_hash = ROUTE_REGISTRY_V6_HASH
        elif version == 6:
            registry = NavigationRegistryV6.model_validate_json(
                canonical_json_bytes(raw), strict=True
            )
            expected_route_registry_hash = ROUTE_REGISTRY_V7_HASH
        elif version == 7:
            registry = NavigationRegistryV7.model_validate_json(
                canonical_json_bytes(raw), strict=True
            )
            expected_route_registry_hash = ROUTE_REGISTRY_V8_HASH
        else:
            raise ValueError(f"unsupported navigation registry version: {version!r}")
    except ValueError as exc:
        raise RegistryError(f"invalid navigation registry resource: {filename}") from exc
    if registry.route_registry_hash != expected_route_registry_hash:
        raise RegistryError("navigation registry is bound to the wrong route registry")
    bound_routes = load_route_registry_by_hash(expected_route_registry_hash)
    expected = tuple(
        (
            route.route_id,
            route.route_version,
            route.entry_validator_id,
            route.allowed_purposes,
        )
        for route in bound_routes.routes
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
    if isinstance(registry, NavigationRegistryV5):
        frozen_v4 = _load_navigation_registry_resource(
            "navigation-registry.v4.json", NAVIGATION_REGISTRY_V4_HASH
        )
        current = registry.model_dump(mode="json")
        frozen = frozen_v4.model_dump(mode="json")
        current["navigation_registry_version"] = 4
        current["route_registry_hash"] = frozen["route_registry_hash"]
        for item in current["routes"]:
            if item["route_id"] == "audit.framing_economics":
                item["route_version"] = 5
        if current != frozen:
            raise RegistryError(
                "navigation registry v5 may advance only the framing audit "
                "and route-registry binding"
            )
    if isinstance(registry, NavigationRegistryV6):
        frozen_v5 = _load_navigation_registry_resource(
            "navigation-registry.v5.json", NAVIGATION_REGISTRY_V5_HASH
        )
        current = registry.model_dump(mode="json")
        frozen = frozen_v5.model_dump(mode="json")
        current["navigation_registry_version"] = 5
        current["route_registry_hash"] = frozen["route_registry_hash"]
        for item in current["routes"]:
            if item["route_id"] == "audit.framing_economics":
                item["route_version"] = 6
        if current != frozen:
            raise RegistryError(
                "navigation registry v6 may advance only the framing audit "
                "and route-registry binding"
            )
    if isinstance(registry, NavigationRegistryV7):
        frozen_v6 = _load_navigation_registry_resource(
            "navigation-registry.v6.json", NAVIGATION_REGISTRY_V6_HASH
        )
        current = registry.model_dump(mode="json")
        frozen = frozen_v6.model_dump(mode="json")
        current["navigation_registry_version"] = 6
        current["route_registry_hash"] = frozen["route_registry_hash"]
        for item in current["routes"]:
            if item["route_id"] == "audit.framing_economics":
                item["route_version"] = 7
        if current != frozen:
            raise RegistryError(
                "navigation registry v7 may advance only the framing audit "
                "and route-registry binding"
            )
    return registry


@lru_cache(maxsize=1)
def load_navigation_registry() -> NavigationRegistryV7:
    """Load the active v7 navigation policy bound to route registry v8."""

    registry = _load_navigation_registry_resource(
        "navigation-registry.v7.json", NAVIGATION_REGISTRY_V7_HASH
    )
    assert isinstance(registry, NavigationRegistryV7)
    return registry


@lru_cache(maxsize=7)
def load_navigation_registry_by_hash(
    navigation_registry_hash: str,
) -> NavigationRegistryLike:
    """Load one exact historical or active navigation registry by identity."""

    resources = {
        NAVIGATION_REGISTRY_V1_HASH: "navigation-registry.v1.json",
        NAVIGATION_REGISTRY_V2_HASH: "navigation-registry.v2.json",
        NAVIGATION_REGISTRY_V3_HASH: "navigation-registry.v3.json",
        NAVIGATION_REGISTRY_V4_HASH: "navigation-registry.v4.json",
        NAVIGATION_REGISTRY_V5_HASH: "navigation-registry.v5.json",
        NAVIGATION_REGISTRY_V6_HASH: "navigation-registry.v6.json",
        NAVIGATION_REGISTRY_V7_HASH: "navigation-registry.v7.json",
    }
    try:
        filename = resources[navigation_registry_hash]
    except KeyError as exc:
        raise RegistryError(
            f"unknown exact navigation registry hash: {navigation_registry_hash}"
        ) from exc
    return _load_navigation_registry_resource(filename, navigation_registry_hash)


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
        "navigation-registry.v2.json": NAVIGATION_REGISTRY_V2_HASH,
        "navigation-registry.v3.json": NAVIGATION_REGISTRY_V3_HASH,
        "navigation-registry.v4.json": NAVIGATION_REGISTRY_V4_HASH,
        "navigation-registry.v5.json": NAVIGATION_REGISTRY_V5_HASH,
        "navigation-registry.v6.json": NAVIGATION_REGISTRY_V6_HASH,
        "navigation-registry.v7.json": NAVIGATION_REGISTRY_V7_HASH,
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
    "NAVIGATION_REGISTRY_HASH",
    "NAVIGATION_REGISTRY_V1_HASH",
    "NAVIGATION_REGISTRY_V2_HASH",
    "NAVIGATION_REGISTRY_V3_HASH",
    "NAVIGATION_REGISTRY_V4_HASH",
    "NAVIGATION_REGISTRY_V5_HASH",
    "NAVIGATION_REGISTRY_V6_HASH",
    "NAVIGATION_REGISTRY_V7_HASH",
    "NavigationRegistryLike",
    "NavigationRegistryV1",
    "NavigationRegistryV2",
    "NavigationRegistryV3",
    "NavigationRegistryV4",
    "NavigationRegistryV5",
    "NavigationRegistryV6",
    "NavigationRegistryV7",
    "NavigationRoutePolicyV1",
    "NavigationRoutePolicyV3",
    "load_compatibility_support",
    "load_host_manifest",
    "load_navigation_registry",
    "load_navigation_registry_by_hash",
    "machine_resource_path",
]
