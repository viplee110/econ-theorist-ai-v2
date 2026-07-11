"""Fail-closed access to the one authoritative Phase 1 route registry.

The registry is data, not an invitation to infer routes from prose or aliases.
This module adds run-entry authorization to the structural validation owned by
``econ_theorist.policy``.
"""

from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType
from typing import Mapping

from .errors import PolicyError, RegistryError
from .models import PrivacyLabel, RouteRegistry, RouteSpec
from .policy import load_route_registry, route_spec


class RouteUnavailableError(RegistryError):
    """A registered route has no implemented consumer in this slice."""


class RouteAuthorizationError(PolicyError):
    """The declared run purpose or grants do not satisfy a route contract."""


PRIVACY_RANK: Mapping[PrivacyLabel, int] = MappingProxyType(
    {
        "public": 0,
        "project_private": 1,
        "restricted": 2,
        "local_only": 3,
    }
)


def load_registry() -> RouteRegistry:
    """Load and validate ``routes/registry.v1.json``.

    ``policy.load_route_registry`` resolves exactly the source-tree registry or
    its installed data-file counterpart.  No caller-supplied registry, alias,
    or prose route is accepted at run time.
    """

    return load_route_registry()


def get_route(route_id: str) -> RouteSpec:
    """Return one exact registered route ID or fail closed."""

    if not isinstance(route_id, str) or not route_id:
        raise RegistryError("route_id must be one non-empty exact route ID")
    return route_spec(route_id, load_registry())


def validate_privacy_clearance(value: str) -> PrivacyLabel:
    """Return a known privacy label without coercing unknown input."""

    if value not in PRIVACY_RANK:
        raise RouteAuthorizationError(f"unknown privacy clearance: {value!r}")
    return value  # type: ignore[return-value]


def clearance_allows(clearance: PrivacyLabel, label: PrivacyLabel) -> bool:
    """Whether ``clearance`` may read material bearing ``label``."""

    return PRIVACY_RANK[clearance] >= PRIVACY_RANK[label]


def authorize_route(
    route_id: str,
    *,
    purpose: str,
    compartments: Iterable[str],
    privacy_clearance: str,
) -> RouteSpec:
    """Authorize entry to one enabled route using explicit grants only.

    Content-level privacy and compartment checks still occur during context
    selection.  This function checks the route contract itself.
    """

    route = get_route(route_id)
    if route.availability != "enabled":
        raise RouteUnavailableError(
            f"registered route {route.route_id!r} is {route.availability}"
        )
    if purpose not in route.allowed_purposes:
        raise RouteAuthorizationError(
            f"purpose {purpose!r} is not allowed for route {route.route_id!r}"
        )

    if isinstance(compartments, str):
        raise RouteAuthorizationError("compartments must be an iterable of grants")
    grants = tuple(compartments)
    if any(not isinstance(item, str) or not item for item in grants):
        raise RouteAuthorizationError("compartment grants must be non-empty strings")
    if len(set(grants)) != len(grants):
        raise RouteAuthorizationError("compartment grants must be unique")

    missing = sorted(set(route.required_compartments).difference(grants))
    if missing:
        raise RouteAuthorizationError(
            "missing required route compartments: " + ", ".join(missing)
        )
    validate_privacy_clearance(privacy_clearance)
    return route


__all__ = [
    "PRIVACY_RANK",
    "RouteAuthorizationError",
    "RouteUnavailableError",
    "authorize_route",
    "clearance_allows",
    "get_route",
    "load_registry",
    "validate_privacy_clearance",
]
