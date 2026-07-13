"""Versioned authority and exact-route policies through Phase 3."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import version as package_version
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .codec import canonical_json_bytes, sha256_digest
from .distribution_resources import (
    DistributionResourceError,
    installed_resource_root,
)
from .errors import AuthorityError, RegistryError
from .models import (
    FACET_ORDER,
    AuthorityLevel,
    Decision,
    DecisionKind,
    Facet,
    RouteRegistry,
    RouteRegistryLike,
    RouteRegistryV2,
    RouteRegistryV3,
    RouteRegistryV4,
    RouteSpec,
    RouteSpecLike,
    RouteSpecV2,
    RouteSpecV3,
    RouteSpecV4,
)

FACETS: tuple[Facet, ...] = FACET_ORDER
DECISION_REGISTRY_V1_VERSION = 1
DECISION_REGISTRY_V2_VERSION = 1
DECISION_REGISTRY_V3_VERSION = 1
DECISION_REGISTRY_V4_VERSION = 1
# Backward-compatible alias for frozen Phase 1 context bytes.
DECISION_REGISTRY_VERSION = DECISION_REGISTRY_V1_VERSION
ROUTE_REGISTRY_V1_HASH = "d9c84001420bd63a82418ee3cfe1776895be69936e921aa8c4790a8966aa6913"
# Filled only after the complete v2 catalog and every instruction bundle are
# content-addressed.  The value is a policy identifier, not a mutable checksum.
ROUTE_REGISTRY_V2_HASH = "cd6e4147ea639f0c3016e88783afcf090ccd8383b70d6efe314599d3909bfa40"
ROUTE_REGISTRY_V3_HASH = "a914276d613e970d68f2ccb5799ad7e912c2edd5b47d098cfbb1f109055ad6cf"
ROUTE_REGISTRY_V4_HASH = "d81276ed9b7482768840ef89980d6cbb81361ca2ff84acee3ab7da7bb67eae7e"
ROUTE_REGISTRY_HASH = ROUTE_REGISTRY_V4_HASH
SELECTOR_VERSION_V1 = "context_selector.v1"
SELECTOR_VERSION_V3 = "context_selector.v2"
SELECTOR_VERSION_V4 = "context_selector.v3"
# Frozen compatibility alias used by historical v1/v2 validation paths.
SELECTOR_VERSION = SELECTOR_VERSION_V1
KERNEL_VERSION = "theory_kernel.v1"
KERNEL_HASH = "1670162bdca5e8b31017c2cb42c48d96bfc627921361904a3c8fe67ee94aca71"
ISOLATION_POLICY = "isolated_route.v1"
VALIDATOR_VERSION = "pydantic_2.13.4"
PINNED_PYDANTIC_VERSION = "2.13.4"
PINNED_PYDANTIC_CORE_VERSION = "2.46.4"


@dataclass(frozen=True, slots=True)
class DecisionRule:
    minimum_authority: AuthorityLevel
    requires_human: bool = True


_L2_KINDS: tuple[DecisionKind, ...] = (
    "G1_question_benchmark",
    "G2_mechanism",
    "G3_formal_base",
    "G4_result_investment",
    "G5_argument_validation",
    "primitive_promotion",
    "solution_concept",
    "main_result_scope",
    "novelty_contribution",
    "argument_spine",
    "narrative_material_order",
    "theory_mode",
    "ambition",
    "field",
    "audience",
    "venue_overlay",
    "submission_constraints",
    "target_profile",
    "voice_charter",
    "manuscript_version_promotion",
    "privacy_declassification",
)
_L3_KINDS: tuple[DecisionKind, ...] = (
    "external_release",
    "submission_handoff",
    "external_communication",
    "destructive_cleanup",
)

DECISION_REGISTRY: Mapping[DecisionKind, DecisionRule] = MappingProxyType(
    {
        **{kind: DecisionRule("L2") for kind in _L2_KINDS},
        **{kind: DecisionRule("L3") for kind in _L3_KINDS},
    }
)
DECISION_POLICY: Mapping[DecisionKind, AuthorityLevel] = MappingProxyType(
    {kind: rule.minimum_authority for kind, rule in DECISION_REGISTRY.items()}
)

AUTHORITY_RANK: Mapping[AuthorityLevel, int] = MappingProxyType(
    {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
)


def validate_runtime_validator() -> None:
    """Fail closed when canonical parsing runs under an unpinned validator."""

    try:
        actual_pydantic = package_version("pydantic")
        actual_core = package_version("pydantic-core")
    except PackageNotFoundError as exc:
        raise RegistryError("the pinned canonical validator is unavailable") from exc
    if (
        actual_pydantic != PINNED_PYDANTIC_VERSION
        or actual_core != PINNED_PYDANTIC_CORE_VERSION
    ):
        raise RegistryError(
            "canonical validator mismatch: expected "
            f"pydantic {PINNED_PYDANTIC_VERSION} / pydantic-core "
            f"{PINNED_PYDANTIC_CORE_VERSION}, got pydantic {actual_pydantic} / "
            f"pydantic-core {actual_core}"
        )


def minimum_authority_for_decision(kind: DecisionKind) -> AuthorityLevel:
    try:
        return DECISION_REGISTRY[kind].minimum_authority
    except KeyError as exc:
        raise AuthorityError(f"unregistered Decision kind: {kind}") from exc


def decision_registry_version_for_route(route: RouteSpecLike) -> int:
    if isinstance(route, RouteSpecV4):
        return DECISION_REGISTRY_V4_VERSION
    if isinstance(route, RouteSpecV3):
        return DECISION_REGISTRY_V3_VERSION
    if isinstance(route, RouteSpecV2):
        return DECISION_REGISTRY_V2_VERSION
    return DECISION_REGISTRY_V1_VERSION


def validate_decision_authority(decision: Decision) -> None:
    rule = DECISION_REGISTRY.get(decision.decision_kind)
    if rule is None:
        raise AuthorityError(f"unregistered Decision kind: {decision.decision_kind}")
    if AUTHORITY_RANK[decision.required_authority] < AUTHORITY_RANK[rule.minimum_authority]:
        raise AuthorityError(
            f"{decision.decision_kind} requires at least {rule.minimum_authority}"
        )
    if (
        rule.requires_human
        and decision.status != "proposed"
        and decision.decider.kind != "human"
    ):
        raise AuthorityError(
            f"effective {decision.decision_kind} Decisions require a human decider"
        )


V1_ROUTE_IDS: tuple[str, ...] = (
    "frame.question_and_benchmarks",
    "decompose.primitives",
    "tournament.mechanisms",
    "freeze.predictions",
    "lab.micro_examples_and_ablations",
    "promote.mechanism",
    "tournament.implementations",
    "promote.formal_base",
    "discover.claims_and_boundaries",
    "verify.claims_proofs_and_interpretation",
    "audit.assumptions_generality_and_absorption",
    "curate.result_portfolio",
    "validate.argument_package",
    "design.reader_path",
    "compose.manuscript_unit",
    "review.manuscript_unit",
    "repair.dependency",
)
CORE_ROUTE_IDS = V1_ROUTE_IDS
V2_ROUTE_IDS: tuple[str, ...] = (
    V1_ROUTE_IDS[0],
    "prepare.blind_case",
    "evaluate.blind_argument_package",
    *V1_ROUTE_IDS[1:],
)
_V3_ASSURANCE_INDEX = V2_ROUTE_IDS.index(
    "verify.claims_proofs_and_interpretation"
) + 1
_V3_REVIEW_END = V2_ROUTE_IDS.index("review.manuscript_unit") + 1
V3_ROUTE_IDS: tuple[str, ...] = (
    *V2_ROUTE_IDS[:_V3_ASSURANCE_INDEX],
    "verify.independent_rederivation",
    "audit.argument_assurance",
    *V2_ROUTE_IDS[_V3_ASSURANCE_INDEX:_V3_REVIEW_END],
    "prepare.reader_probe",
    "answer.reader_probe",
    "adjudicate.reader_probe",
    "close.manuscript_review",
    "record.human_effort",
    *V2_ROUTE_IDS[_V3_REVIEW_END:],
)
V3_NATIVE_ROUTE_IDS = frozenset(
    {
        "verify.independent_rederivation",
        "audit.argument_assurance",
        "design.reader_path",
        "compose.manuscript_unit",
        "review.manuscript_unit",
        "prepare.reader_probe",
        "answer.reader_probe",
        "adjudicate.reader_probe",
        "close.manuscript_review",
        "record.human_effort",
    }
)
V4_ROUTE_IDS: tuple[str, ...] = (
    *V3_ROUTE_IDS,
    "map.obligation_predicate",
    "audit.obligation_predicate",
    "resolve.profile_stack",
    "diagnose.reader_problem",
    "retrieve.craft_moves",
    "compose.profiled_manuscript_unit",
    "review.craft_realization",
    "close.profile_craft_review",
)
V4_NATIVE_ROUTE_IDS = frozenset(
    {
        "map.obligation_predicate",
        "audit.obligation_predicate",
        "resolve.profile_stack",
        "diagnose.reader_problem",
        "retrieve.craft_moves",
        "compose.profiled_manuscript_unit",
        "review.craft_realization",
        "close.profile_craft_review",
    }
)
V1_ENABLED_ROUTE_IDS = frozenset(
    {"frame.question_and_benchmarks", "repair.dependency"}
)
V2_ENABLED_ROUTE_IDS = frozenset(V2_ROUTE_IDS).difference(
    {"design.reader_path", "compose.manuscript_unit", "review.manuscript_unit"}
)
V3_ENABLED_ROUTE_IDS = frozenset(V3_ROUTE_IDS)
V4_ENABLED_ROUTE_IDS = frozenset(V4_ROUTE_IDS)
ROUTE_REGISTRY_HASHES: Mapping[int, str] = MappingProxyType(
    {
        1: ROUTE_REGISTRY_V1_HASH,
        2: ROUTE_REGISTRY_V2_HASH,
        3: ROUTE_REGISTRY_V3_HASH,
        4: ROUTE_REGISTRY_V4_HASH,
    }
)


def _default_registry_path() -> Path:
    return _routes_root() / "registry.v4.json"


def _routes_root() -> Path:
    source_root = Path(__file__).resolve().parents[2] / "routes"
    if (source_root / "registry.v1.json").is_file():
        return source_root
    try:
        installed_root = installed_resource_root() / "routes"
    except DistributionResourceError as exc:
        raise RegistryError(
            "cannot locate source or installed route policy resources"
        ) from exc
    if not installed_root.is_dir():
        raise RegistryError(
            f"installed route policy resources are missing: {installed_root}"
        )
    return installed_root


def registry_hash(registry: RouteRegistryLike) -> str:
    """Return the exact pinned identity of one validated catalog."""

    expected = ROUTE_REGISTRY_HASHES.get(registry.registry_version)
    if expected is None:
        raise RegistryError(
            f"unsupported route registry version: {registry.registry_version}"
        )
    actual = sha256_digest(canonical_json_bytes(registry))
    if actual != expected:
        raise RegistryError(
            f"route registry v{registry.registry_version} differs from its pinned bytes"
        )
    return expected


def validate_route_registry(registry: RouteRegistryLike) -> RouteRegistryLike:
    ids = tuple(route.route_id for route in registry.routes)
    expected_ids = {
        1: V1_ROUTE_IDS,
        2: V2_ROUTE_IDS,
        3: V3_ROUTE_IDS,
        4: V4_ROUTE_IDS,
    }[registry.registry_version]
    if ids != expected_ids:
        raise RegistryError(
            f"route registry v{registry.registry_version} must contain its exact ordered route IDs"
        )
    if registry.aliases:
        raise RegistryError("route registries have no implicit route aliases")
    enabled = {route.route_id for route in registry.routes if route.availability == "enabled"}
    expected_enabled = {
        1: V1_ENABLED_ROUTE_IDS,
        2: V2_ENABLED_ROUTE_IDS,
        3: V3_ENABLED_ROUTE_IDS,
        4: V4_ENABLED_ROUTE_IDS,
    }[registry.registry_version]
    if enabled != expected_enabled:
        raise RegistryError(
            f"route registry v{registry.registry_version} has the wrong enabled set"
        )
    if any(route.authority_ceiling != "L1" for route in registry.routes):
        raise RegistryError("routes may propose but not exercise L2/L3 authority")
    if registry.registry_version == 3:
        versions = {route.route_id: route.route_version for route in registry.routes}
        wrong_versions = {
            route_id: route_version
            for route_id, route_version in versions.items()
            if (route_id in V3_NATIVE_ROUTE_IDS) != (route_version == 3)
        }
        if wrong_versions:
            raise RegistryError(
                "registry v3 must advance only its ten native routes to version 3"
            )

        frozen_v2 = load_route_registry(_routes_root() / "registry.v2.json")
        frozen_by_id = {route.route_id: route for route in frozen_v2.routes}
        for route in registry.routes:
            if route.route_id in V3_NATIVE_ROUTE_IDS:
                continue
            if route.model_dump(mode="json") != frozen_by_id[route.route_id].model_dump(
                mode="json"
            ):
                raise RegistryError(
                    f"registry v3 route {route.route_id!r} differs from frozen v2 semantics"
                )
    if registry.registry_version == 4:
        versions = {route.route_id: route.route_version for route in registry.routes}
        wrong_versions = {
            route_id: route_version
            for route_id, route_version in versions.items()
            if (route_id in V4_NATIVE_ROUTE_IDS) != (route_version == 4)
            and route_id not in V3_NATIVE_ROUTE_IDS
        }
        wrong_phase3_versions = {
            route_id: route_version
            for route_id, route_version in versions.items()
            if route_id in V3_NATIVE_ROUTE_IDS and route_version != 3
        }
        if wrong_versions or wrong_phase3_versions:
            raise RegistryError(
                "registry v4 must advance only its eight additive routes to version 4"
            )

        frozen_v3 = load_route_registry(_routes_root() / "registry.v3.json")
        frozen_by_id = {route.route_id: route for route in frozen_v3.routes}
        for route in registry.routes:
            if route.route_id in V4_NATIVE_ROUTE_IDS:
                continue
            if route.model_dump(mode="json") != frozen_by_id[route.route_id].model_dump(
                mode="json"
            ):
                raise RegistryError(
                    f"registry v4 route {route.route_id!r} differs from frozen v3 semantics"
                )
    registry_hash(registry)
    return registry


@lru_cache(maxsize=8)
def load_route_registry(path: str | Path | None = None) -> RouteRegistryLike:
    validate_runtime_validator()
    source = Path(path) if path is not None else _default_registry_path()
    try:
        payload = source.read_bytes()
    except OSError as exc:
        raise RegistryError(f"cannot read route registry: {source}") from exc
    try:
        decoded = json.loads(payload.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("registry is not an object")
        version = decoded.get("registry_version")
        if version == 1:
            registry: RouteRegistryLike = RouteRegistry.model_validate_json(
                payload, strict=True
            )
        elif version == 2:
            registry = RouteRegistryV2.model_validate_json(payload, strict=True)
        elif version == 3:
            registry = RouteRegistryV3.model_validate_json(payload, strict=True)
        elif version == 4:
            registry = RouteRegistryV4.model_validate_json(payload, strict=True)
        else:
            raise ValueError(f"unsupported registry_version: {version!r}")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RegistryError(f"invalid route registry: {source}") from exc
    return validate_route_registry(registry)


@lru_cache(maxsize=4)
def load_route_registry_by_hash(route_registry_hash: str) -> RouteRegistryLike:
    """Resolve historical policy by exact manifest-bound registry hash."""

    versions = [
        version
        for version, digest in ROUTE_REGISTRY_HASHES.items()
        if digest == route_registry_hash
    ]
    if len(versions) != 1:
        raise RegistryError(f"unknown exact route registry hash: {route_registry_hash}")
    return load_route_registry(_routes_root() / f"registry.v{versions[0]}.json")


def route_spec(
    route_id: str, registry: RouteRegistryLike | None = None
) -> RouteSpecLike:
    active_registry = registry or load_route_registry()
    for route in active_registry.routes:
        if route.route_id == route_id:
            return route
    raise RegistryError(f"unknown exact route ID: {route_id}")


def route_spec_by_hash(route_id: str, route_registry_hash: str) -> RouteSpecLike:
    return route_spec(route_id, load_route_registry_by_hash(route_registry_hash))


def registry_hash_for_route(route: RouteSpecLike) -> str:
    if isinstance(route, RouteSpec):
        return ROUTE_REGISTRY_V1_HASH
    if isinstance(route, RouteSpecV4):
        return ROUTE_REGISTRY_V4_HASH
    if isinstance(route, RouteSpecV3):
        return ROUTE_REGISTRY_V3_HASH
    if isinstance(route, RouteSpecV2):
        return ROUTE_REGISTRY_V2_HASH
    raise RegistryError(f"unsupported route specification type: {type(route).__name__}")


def selector_version_for_route(route: RouteSpecLike) -> str:
    """Return the exact selector policy without changing historical manifests."""

    if isinstance(route, RouteSpecV4):
        if route.route_id in V4_NATIVE_ROUTE_IDS:
            return SELECTOR_VERSION_V4
        if route.route_id in V3_NATIVE_ROUTE_IDS:
            return SELECTOR_VERSION_V3
        return SELECTOR_VERSION_V1
    if isinstance(route, RouteSpecV3) and route.route_id in V3_NATIVE_ROUTE_IDS:
        return SELECTOR_VERSION_V3
    return SELECTOR_VERSION_V1


def instruction_bundle_bytes(route: RouteSpecLike) -> bytes:
    """Load one enabled route's exact, content-addressed instruction bundle."""

    if route.instruction_bundle_id is None or route.instruction_bundle_hash is None:
        raise RegistryError(f"route {route.route_id!r} has no instruction bundle")
    expected_id = f"{route.route_id}.v{route.route_version}"
    if route.instruction_bundle_id != expected_id:
        raise RegistryError(
            f"route {route.route_id!r} has a noncanonical instruction bundle ID"
        )
    path = _routes_root() / "instructions" / f"{route.instruction_bundle_id}.txt"
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise RegistryError(f"cannot read route instruction bundle: {path}") from exc
    if sha256_digest(payload) != route.instruction_bundle_hash:
        raise RegistryError(
            f"route instruction bundle hash mismatch: {route.instruction_bundle_id}"
        )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RegistryError("route instruction bundle is not UTF-8") from exc
    if "\r" in text or "\x00" in text:
        raise RegistryError("route instruction bundle is not canonical LF UTF-8 text")
    if not text.strip():
        raise RegistryError("route instruction bundle is empty")
    return payload


@lru_cache(maxsize=1)
def theory_kernel() -> Mapping[str, Any]:
    """Load the independently versioned always-on theory kernel."""

    path = _routes_root() / "instructions" / f"{KERNEL_VERSION}.json"
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise RegistryError(f"cannot read theory kernel: {path}") from exc
    if sha256_digest(payload) != KERNEL_HASH:
        raise RegistryError("theory kernel hash does not match the pinned policy")
    import json

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RegistryError("theory kernel is not canonical UTF-8 JSON") from exc
    canonical_payload = payload[:-1] if payload.endswith(b"\n") else payload
    if not isinstance(decoded, dict) or canonical_json_bytes(decoded) != canonical_payload:
        raise RegistryError(
            "theory kernel must be one canonical JSON object with at most one LF"
        )
    return MappingProxyType(decoded)
