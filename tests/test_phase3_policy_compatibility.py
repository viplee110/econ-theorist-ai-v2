from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT

from econ_theorist.models import RouteSpecV3
from econ_theorist.policy import (
    ROUTE_REGISTRY_HASH,
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V3_HASH,
    SELECTOR_VERSION_V1,
    SELECTOR_VERSION_V3,
    V1_ENABLED_ROUTE_IDS,
    V1_ROUTE_IDS,
    V2_ENABLED_ROUTE_IDS,
    V2_ROUTE_IDS,
    V3_ENABLED_ROUTE_IDS,
    V3_NATIVE_ROUTE_IDS,
    V3_ROUTE_IDS,
    instruction_bundle_bytes,
    load_route_registry,
    load_route_registry_by_hash,
    registry_hash,
    selector_version_for_route,
)
from scripts.export_authoring_schemas import check as check_authoring_schemas


class Phase3PolicyCompatibilityTests(unittest.TestCase):
    def test_historical_catalogs_remain_exact_and_active_v3_is_distinct(self) -> None:
        expected = (
            (ROUTE_REGISTRY_V1_HASH, 1, V1_ROUTE_IDS, V1_ENABLED_ROUTE_IDS),
            (ROUTE_REGISTRY_V2_HASH, 2, V2_ROUTE_IDS, V2_ENABLED_ROUTE_IDS),
            (ROUTE_REGISTRY_V3_HASH, 3, V3_ROUTE_IDS, V3_ENABLED_ROUTE_IDS),
        )
        for digest, version, route_ids, enabled_ids in expected:
            with self.subTest(version=version):
                catalog = load_route_registry_by_hash(digest)
                self.assertEqual(catalog.registry_version, version)
                self.assertEqual(registry_hash(catalog), digest)
                self.assertEqual(
                    tuple(route.route_id for route in catalog.routes), route_ids
                )
                self.assertEqual(
                    {
                        route.route_id
                        for route in catalog.routes
                        if route.availability == "enabled"
                    },
                    set(enabled_ids),
                )

        active = load_route_registry()
        self.assertEqual(active.registry_version, 3)
        self.assertEqual(ROUTE_REGISTRY_HASH, ROUTE_REGISTRY_V3_HASH)

    def test_v3_preserves_v2_route_versions_and_versions_native_routes(self) -> None:
        catalog = load_route_registry_by_hash(ROUTE_REGISTRY_V3_HASH)
        routes = {route.route_id: route for route in catalog.routes}
        self.assertTrue(all(isinstance(route, RouteSpecV3) for route in routes.values()))
        for route_id, route in routes.items():
            with self.subTest(route=route_id):
                if route_id in V3_NATIVE_ROUTE_IDS:
                    self.assertEqual(route.route_version, 3)
                    self.assertEqual(selector_version_for_route(route), SELECTOR_VERSION_V3)
                else:
                    self.assertEqual(route.route_version, 2)
                    self.assertEqual(selector_version_for_route(route), SELECTOR_VERSION_V1)
                self.assertTrue(instruction_bundle_bytes(route))

    def test_phase3_authoring_schemas_are_committed_exactly(self) -> None:
        self.assertTrue(
            check_authoring_schemas(
                REPOSITORY_ROOT / "schemas" / "authoring" / "v1"
            )
        )


if __name__ == "__main__":
    unittest.main()
