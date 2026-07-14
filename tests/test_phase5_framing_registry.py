"""Frozen-policy and additive-registry checks for the framing audit slice."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import sha256_digest
from econ_theorist.machine.resources import (
    NAVIGATION_REGISTRY_HASH,
    NAVIGATION_REGISTRY_V1_HASH,
    NAVIGATION_REGISTRY_V2_HASH,
    NavigationRegistryV1,
    NavigationRegistryV2,
    load_navigation_registry,
    load_navigation_registry_by_hash,
)
from econ_theorist.models import RouteSpecV5
from econ_theorist.policy import (
    KERNEL_HASH,
    ROUTE_REGISTRY_HASH,
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V3_HASH,
    ROUTE_REGISTRY_V4_HASH,
    ROUTE_REGISTRY_V5_HASH,
    V4_ROUTE_IDS,
    V5_ENABLED_ROUTE_IDS,
    V5_NATIVE_ROUTE_IDS,
    V5_ROUTE_IDS,
    instruction_bundle_bytes,
    load_route_registry,
    load_route_registry_by_hash,
    registry_hash,
)


FROZEN_RAW_REGISTRY_HASHES = {
    1: "c0badd3e4af4dc31f17c6352a07d7d3da359fb1eeb86e2799a98ca1170c4cb37",
    2: "3279ca4de2408dfe56766b2339616d00ebab4071d9a34d2874753d9f029ff55d",
    3: "4020bde117264400e0d9aa2571b5ba73baaaf7cb5939faecc1c39c6f7c952875",
    4: "88285c9f466c0790050f38fd8d336464d1e16f45f4ac88edf11c50f31d732a32",
}
FROZEN_CANONICAL_REGISTRY_HASHES = {
    1: "d9c84001420bd63a82418ee3cfe1776895be69936e921aa8c4790a8966aa6913",
    2: "cd6e4147ea639f0c3016e88783afcf090ccd8383b70d6efe314599d3909bfa40",
    3: "a914276d613e970d68f2ccb5799ad7e912c2edd5b47d098cfbb1f109055ad6cf",
    4: "d81276ed9b7482768840ef89980d6cbb81361ca2ff84acee3ab7da7bb67eae7e",
}
FROZEN_NAVIGATION_V1_RAW_HASH = (
    "970a40842ce298945b67bbdd65f4191d8506565de7363324bb79f504e2cdacbd"
)


class Phase5FramingRegistryTests(unittest.TestCase):
    def test_v1_through_v4_registry_and_instruction_bytes_remain_frozen(self) -> None:
        constants = {
            1: ROUTE_REGISTRY_V1_HASH,
            2: ROUTE_REGISTRY_V2_HASH,
            3: ROUTE_REGISTRY_V3_HASH,
            4: ROUTE_REGISTRY_V4_HASH,
        }
        for version, expected_raw_hash in FROZEN_RAW_REGISTRY_HASHES.items():
            with self.subTest(registry_version=version):
                path = REPOSITORY_ROOT / "routes" / f"registry.v{version}.json"
                self.assertEqual(sha256_digest(path.read_bytes()), expected_raw_hash)
                self.assertEqual(
                    constants[version], FROZEN_CANONICAL_REGISTRY_HASHES[version]
                )
                registry = load_route_registry_by_hash(constants[version])
                self.assertEqual(registry_hash(registry), constants[version])
                for route in registry.routes:
                    if route.availability == "enabled":
                        self.assertEqual(
                            sha256_digest(instruction_bundle_bytes(route)),
                            route.instruction_bundle_hash,
                        )

        kernel = REPOSITORY_ROOT / "routes" / "instructions" / "theory_kernel.v1.json"
        self.assertEqual(sha256_digest(kernel.read_bytes()), KERNEL_HASH)
        navigation_v1 = REPOSITORY_ROOT / "machine" / "navigation-registry.v1.json"
        self.assertEqual(
            sha256_digest(navigation_v1.read_bytes()),
            FROZEN_NAVIGATION_V1_RAW_HASH,
        )

    def test_v5_preserves_v4_except_framing_repair_and_adds_framing_audit(self) -> None:
        v4 = load_route_registry_by_hash(ROUTE_REGISTRY_V4_HASH)
        v5 = load_route_registry_by_hash(ROUTE_REGISTRY_V5_HASH)
        v4_by_id = {route.route_id: route for route in v4.routes}
        v5_by_id = {route.route_id: route for route in v5.routes}

        self.assertEqual(V5_ROUTE_IDS[:-1], V4_ROUTE_IDS)
        self.assertEqual(
            V5_NATIVE_ROUTE_IDS,
            frozenset({"audit.framing_economics", "repair.dependency"}),
        )
        self.assertEqual(
            set(V5_ROUTE_IDS).difference(V4_ROUTE_IDS),
            {"audit.framing_economics"},
        )
        self.assertEqual(V5_ENABLED_ROUTE_IDS, frozenset(V5_ROUTE_IDS))
        self.assertEqual(len(v5.routes), len(v4.routes) + 1)
        self.assertTrue(all(isinstance(route, RouteSpecV5) for route in v5.routes))

        for route_id in V4_ROUTE_IDS:
            if route_id == "repair.dependency":
                continue
            with self.subTest(carried_route=route_id):
                old = v4_by_id[route_id]
                carried = v5_by_id[route_id]
                self.assertEqual(
                    carried.model_dump(mode="json"), old.model_dump(mode="json")
                )
                self.assertEqual(
                    instruction_bundle_bytes(carried), instruction_bundle_bytes(old)
                )

        old_repair = v4_by_id["repair.dependency"]
        repair = v5_by_id["repair.dependency"]
        self.assertEqual(repair.route_version, 5)
        self.assertEqual(repair.instruction_bundle_id, "repair.dependency.v5")
        self.assertEqual(
            repair.entry_validator_id, "framing_repair_route_entry.v1"
        )
        self.assertEqual(repair.exit_validator_id, "framing_repair_route_exit.v1")
        self.assertEqual(
            set(repair.allowed_entity_types),
            set(old_repair.allowed_entity_types).difference({"GateDossier"}),
        )
        self.assertNotIn("FramingQualityBundle", repair.allowed_entity_types)
        for field in (
            "allowed_operations",
            "allowed_purposes",
            "allowed_relation_types",
            "authority_ceiling",
            "availability",
            "required_compartments",
            "required_gate_kinds",
            "required_input_entities",
            "required_output_entities",
            "required_output_relations",
        ):
            with self.subTest(repair_preserved_field=field):
                self.assertEqual(getattr(repair, field), getattr(old_repair, field))
        repair_instruction = instruction_bundle_bytes(repair)
        self.assertEqual(
            sha256_digest(repair_instruction), repair.instruction_bundle_hash
        )
        self.assertIn(b"one-stale-root repair contract", repair_instruction)
        self.assertIn(b"proposed_action=revise_framing", repair_instruction)
        self.assertIn(
            b"Never create, supersede, or reinterpret a GateDossier or FramingQualityBundle",
            repair_instruction,
        )

        audit = v5_by_id["audit.framing_economics"]
        self.assertEqual(audit.route_version, 5)
        self.assertEqual(audit.allowed_purposes, ("scientific_framing_audit",))
        self.assertEqual(
            audit.allowed_operations,
            (
                "blocker.record",
                "entity.create",
                "entity.supersede",
                "relation.create",
                "route.outcome",
            ),
        )
        self.assertEqual(audit.allowed_entity_types, ("FramingQualityBundle", "GateDossier"))
        self.assertEqual(audit.allowed_relation_types, ("audits", "governs"))
        self.assertEqual(
            tuple(
                (item.entity_type, item.min_count, item.max_count)
                for item in audit.required_input_entities
            ),
            (
                ("BenchmarkSet", 1, 1),
                ("FramingQualityBundle", 0, 1),
                ("GateDossier", 1, 1),
                ("PrimitiveGraph", 1, 1),
                ("ResearchQuestion", 1, 1),
            ),
        )
        self.assertEqual(
            tuple(
                (item.entity_type, item.min_count, item.max_count)
                for item in audit.required_output_entities
            ),
            (("FramingQualityBundle", 1, 1), ("GateDossier", 1, 1)),
        )
        self.assertEqual(
            tuple(
                (item.relation_type, item.min_count, item.max_count)
                for item in audit.required_output_relations
            ),
            (("audits", 4, 4), ("governs", 1, 1)),
        )
        self.assertEqual(audit.entry_validator_id, "framing_quality_route_entry.v1")
        self.assertEqual(audit.exit_validator_id, "framing_quality_route_exit.v1")
        instruction = instruction_bundle_bytes(audit)
        self.assertEqual(sha256_digest(instruction), audit.instruction_bundle_hash)
        self.assertIn(b"economic meaning", instruction)
        self.assertIn(b"never record, confirm, or imply an effective G1 decision", instruction)

    def test_navigation_contract_admits_first_audit_and_five_input_continuation(self) -> None:
        route = load_route_registry_by_hash(ROUTE_REGISTRY_V5_HASH).routes[-1]
        requirements = {
            item.entity_type: (item.min_count, item.max_count)
            for item in route.required_input_entities
        }
        policy = load_navigation_registry().routes[-1]

        self.assertEqual(requirements["FramingQualityBundle"], (0, 1))
        self.assertEqual(sum(item[0] for item in requirements.values()), 4)
        self.assertEqual(sum(item[1] or 0 for item in requirements.values()), 5)
        self.assertEqual(policy.route_id, route.route_id)
        self.assertEqual(policy.selector_id, "registry_cardinality.v1")

    def test_route_and_navigation_v2_are_active_while_v1_remains_addressable(self) -> None:
        active_routes = load_route_registry()
        self.assertEqual(active_routes.registry_version, 5)
        self.assertEqual(ROUTE_REGISTRY_HASH, ROUTE_REGISTRY_V5_HASH)
        self.assertEqual(registry_hash(active_routes), ROUTE_REGISTRY_V5_HASH)

        active_navigation = load_navigation_registry()
        self.assertIsInstance(active_navigation, NavigationRegistryV2)
        self.assertEqual(NAVIGATION_REGISTRY_HASH, NAVIGATION_REGISTRY_V2_HASH)
        self.assertEqual(active_navigation.navigation_registry_version, 2)
        self.assertEqual(active_navigation.route_registry_hash, ROUTE_REGISTRY_V5_HASH)
        policy = active_navigation.routes[-1]
        self.assertEqual(policy.route_id, "audit.framing_economics")
        self.assertEqual(policy.selector_id, "registry_cardinality.v1")
        self.assertEqual(policy.purpose, "scientific_framing_audit")
        self.assertEqual(policy.default_budget_units, 18000)

        historical = load_navigation_registry_by_hash(NAVIGATION_REGISTRY_V1_HASH)
        self.assertIsInstance(historical, NavigationRegistryV1)
        self.assertEqual(historical.navigation_registry_version, 1)
        self.assertEqual(historical.route_registry_hash, ROUTE_REGISTRY_V4_HASH)


if __name__ == "__main__":
    unittest.main()
