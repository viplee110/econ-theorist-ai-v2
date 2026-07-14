"""Frozen-catalog and additive-registry contracts for Phase 4."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import sha256_digest
from econ_theorist.models import RouteSpecV4
from econ_theorist.policy import (
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V3_HASH,
    ROUTE_REGISTRY_V4_HASH,
    SELECTOR_VERSION_V1,
    SELECTOR_VERSION_V3,
    SELECTOR_VERSION_V4,
    V1_ENABLED_ROUTE_IDS,
    V1_ROUTE_IDS,
    V2_ENABLED_ROUTE_IDS,
    V2_ROUTE_IDS,
    V3_ENABLED_ROUTE_IDS,
    V3_NATIVE_ROUTE_IDS,
    V3_ROUTE_IDS,
    V4_ENABLED_ROUTE_IDS,
    V4_NATIVE_ROUTE_IDS,
    V4_ROUTE_IDS,
    instruction_bundle_bytes,
    load_route_registry_by_hash,
    registry_hash,
    selector_version_for_route,
)


FROZEN_REGISTRY_HASHES = {
    1: "d9c84001420bd63a82418ee3cfe1776895be69936e921aa8c4790a8966aa6913",
    2: "cd6e4147ea639f0c3016e88783afcf090ccd8383b70d6efe314599d3909bfa40",
    3: "a914276d613e970d68f2ccb5799ad7e912c2edd5b47d098cfbb1f109055ad6cf",
}
PHASE4_REGISTRY_HASH = (
    "d81276ed9b7482768840ef89980d6cbb81361ca2ff84acee3ab7da7bb67eae7e"
)

PHASE4_NATIVE_ROUTE_IDS = frozenset(
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


class Phase4PolicyCompatibilityTests(unittest.TestCase):
    def test_v1_v2_v3_catalogs_and_instruction_bytes_remain_frozen(self) -> None:
        expected = (
            (
                ROUTE_REGISTRY_V1_HASH,
                1,
                V1_ROUTE_IDS,
                V1_ENABLED_ROUTE_IDS,
            ),
            (
                ROUTE_REGISTRY_V2_HASH,
                2,
                V2_ROUTE_IDS,
                V2_ENABLED_ROUTE_IDS,
            ),
            (
                ROUTE_REGISTRY_V3_HASH,
                3,
                V3_ROUTE_IDS,
                V3_ENABLED_ROUTE_IDS,
            ),
        )
        self.assertEqual(ROUTE_REGISTRY_V1_HASH, FROZEN_REGISTRY_HASHES[1])
        self.assertEqual(ROUTE_REGISTRY_V2_HASH, FROZEN_REGISTRY_HASHES[2])
        self.assertEqual(ROUTE_REGISTRY_V3_HASH, FROZEN_REGISTRY_HASHES[3])

        for digest, version, route_ids, enabled_ids in expected:
            with self.subTest(registry_version=version):
                catalog = load_route_registry_by_hash(digest)
                self.assertEqual(catalog.registry_version, version)
                self.assertEqual(registry_hash(catalog), FROZEN_REGISTRY_HASHES[version])
                self.assertEqual(
                    tuple(route.route_id for route in catalog.routes), route_ids
                )
                self.assertEqual(
                    frozenset(
                        route.route_id
                        for route in catalog.routes
                        if route.availability == "enabled"
                    ),
                    enabled_ids,
                )
                for route in catalog.routes:
                    if route.availability != "enabled":
                        continue
                    with self.subTest(
                        registry_version=version, route_id=route.route_id
                    ):
                        bundle = instruction_bundle_bytes(route)
                        self.assertEqual(
                            sha256_digest(bundle), route.instruction_bundle_hash
                        )
                        self.assertEqual(
                            route.instruction_bundle_id,
                            f"{route.route_id}.v{route.route_version}",
                        )

    def test_v4_is_strictly_additive_and_preserves_every_v3_route_object(self) -> None:
        frozen_v3 = load_route_registry_by_hash(ROUTE_REGISTRY_V3_HASH)
        v4 = load_route_registry_by_hash(ROUTE_REGISTRY_V4_HASH)
        frozen_by_id = {route.route_id: route for route in frozen_v3.routes}
        v4_by_id = {route.route_id: route for route in v4.routes}

        self.assertEqual(V4_NATIVE_ROUTE_IDS, PHASE4_NATIVE_ROUTE_IDS)
        self.assertEqual(
            frozenset(V4_ROUTE_IDS).difference(V3_ROUTE_IDS),
            PHASE4_NATIVE_ROUTE_IDS,
        )
        self.assertEqual(V4_ROUTE_IDS[: len(V3_ROUTE_IDS)], V3_ROUTE_IDS)
        self.assertEqual(V4_ENABLED_ROUTE_IDS, frozenset(V4_ROUTE_IDS))
        self.assertTrue(all(isinstance(route, RouteSpecV4) for route in v4.routes))

        for route_id in V3_ROUTE_IDS:
            with self.subTest(frozen_route=route_id):
                old = frozen_by_id[route_id]
                carried = v4_by_id[route_id]
                self.assertEqual(
                    carried.model_dump(mode="json"), old.model_dump(mode="json")
                )
                self.assertEqual(
                    instruction_bundle_bytes(carried), instruction_bundle_bytes(old)
                )

        version_four_ids = {
            route.route_id for route in v4.routes if route.route_version == 4
        }
        self.assertEqual(version_four_ids, PHASE4_NATIVE_ROUTE_IDS)
        self.assertEqual(len(version_four_ids), 8)
        for route_id in PHASE4_NATIVE_ROUTE_IDS:
            with self.subTest(native_route=route_id):
                route = v4_by_id[route_id]
                self.assertEqual(route.route_version, 4)
                self.assertEqual(route.availability, "enabled")
                self.assertTrue(instruction_bundle_bytes(route))

        mapping = v4_by_id["map.obligation_predicate"]
        self.assertIn("artifact.register", mapping.allowed_operations)
        self.assertEqual(
            mapping.allowed_operations,
            (
                "artifact.register",
                "blocker.record",
                "entity.create",
                "relation.create",
                "route.outcome",
            ),
        )
        audit = v4_by_id["audit.obligation_predicate"]
        self.assertEqual(
            audit.allowed_operations,
            (
                "artifact.register",
                "blocker.record",
                "entity.create",
                "relation.create",
                "route.outcome",
            ),
        )
        craft_review = v4_by_id["review.craft_realization"]
        self.assertEqual(
            craft_review.allowed_operations,
            (
                "artifact.register",
                "blocker.record",
                "entity.create",
                "relation.create",
                "route.outcome",
            ),
        )
        craft_review_inputs = {
            requirement.entity_type: (
                requirement.min_count,
                requirement.max_count,
            )
            for requirement in craft_review.required_input_entities
        }
        diagnosis_inputs = {
            requirement.entity_type: (
                requirement.min_count,
                requirement.max_count,
            )
            for requirement in v4_by_id[
                "diagnose.reader_problem"
            ].required_input_entities
        }
        self.assertEqual(diagnosis_inputs["ReviewClosure"], (0, 1))
        self.assertEqual(diagnosis_inputs["RevisionBrief"], (0, 1))
        self.assertEqual(craft_review_inputs["ReaderPath"], (1, 1))
        self.assertEqual(craft_review_inputs["ResultContractSet"], (1, 1))
        self.assertEqual(craft_review_inputs["ReviewClosure"], (1, 1))
        self.assertEqual(craft_review_inputs["ReviewRecord"], (3, 3))

    def test_selector_versions_follow_route_semantics_not_active_catalog_age(self) -> None:
        v1 = load_route_registry_by_hash(ROUTE_REGISTRY_V1_HASH)
        v2 = load_route_registry_by_hash(ROUTE_REGISTRY_V2_HASH)
        v3 = load_route_registry_by_hash(ROUTE_REGISTRY_V3_HASH)
        v4 = load_route_registry_by_hash(ROUTE_REGISTRY_V4_HASH)

        for route in (*v1.routes, *v2.routes):
            with self.subTest(registry=route.route_version, route=route.route_id):
                self.assertEqual(selector_version_for_route(route), SELECTOR_VERSION_V1)

        for route in v3.routes:
            with self.subTest(registry=3, route=route.route_id):
                expected = (
                    SELECTOR_VERSION_V3
                    if route.route_id in V3_NATIVE_ROUTE_IDS
                    else SELECTOR_VERSION_V1
                )
                self.assertEqual(selector_version_for_route(route), expected)

        for route in v4.routes:
            with self.subTest(registry=4, route=route.route_id):
                if route.route_id in V4_NATIVE_ROUTE_IDS:
                    expected = SELECTOR_VERSION_V4
                elif route.route_id in V3_NATIVE_ROUTE_IDS:
                    expected = SELECTOR_VERSION_V3
                else:
                    expected = SELECTOR_VERSION_V1
                self.assertEqual(selector_version_for_route(route), expected)

    def test_v4_remains_an_exact_historical_catalog(self) -> None:
        historical = load_route_registry_by_hash(ROUTE_REGISTRY_V4_HASH)
        self.assertEqual(historical.registry_version, 4)
        self.assertEqual(ROUTE_REGISTRY_V4_HASH, PHASE4_REGISTRY_HASH)
        self.assertEqual(registry_hash(historical), ROUTE_REGISTRY_V4_HASH)
        self.assertEqual(
            tuple(route.route_id for route in historical.routes), V4_ROUTE_IDS
        )


if __name__ == "__main__":
    unittest.main()
