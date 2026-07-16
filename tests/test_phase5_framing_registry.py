"""Frozen-policy and additive-registry checks for the framing audit slice."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import sha256_digest
from econ_theorist.machine.resources import (
    NAVIGATION_REGISTRY_HASH,
    NAVIGATION_REGISTRY_V1_HASH,
    NAVIGATION_REGISTRY_V2_HASH,
    NAVIGATION_REGISTRY_V3_HASH,
    NAVIGATION_REGISTRY_V4_HASH,
    NAVIGATION_REGISTRY_V5_HASH,
    NAVIGATION_REGISTRY_V6_HASH,
    NAVIGATION_REGISTRY_V7_HASH,
    NavigationRegistryV1,
    NavigationRegistryV2,
    NavigationRegistryV3,
    NavigationRegistryV4,
    NavigationRegistryV5,
    NavigationRegistryV6,
    NavigationRegistryV7,
    load_navigation_registry,
    load_navigation_registry_by_hash,
)
from econ_theorist.models import RouteSpecV5, RouteSpecV6, RouteSpecV7, RouteSpecV8
from econ_theorist.policy import (
    KERNEL_HASH,
    ROUTE_REGISTRY_HASH,
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V3_HASH,
    ROUTE_REGISTRY_V4_HASH,
    ROUTE_REGISTRY_V5_HASH,
    ROUTE_REGISTRY_V6_HASH,
    ROUTE_REGISTRY_V7_HASH,
    ROUTE_REGISTRY_V8_HASH,
    V4_ROUTE_IDS,
    V5_ENABLED_ROUTE_IDS,
    V5_NATIVE_ROUTE_IDS,
    V5_ROUTE_IDS,
    V6_ENABLED_ROUTE_IDS,
    V6_NATIVE_ROUTE_IDS,
    V6_ROUTE_IDS,
    V7_ENABLED_ROUTE_IDS,
    V7_NATIVE_ROUTE_IDS,
    V7_ROUTE_IDS,
    V8_ENABLED_ROUTE_IDS,
    V8_NATIVE_ROUTE_IDS,
    V8_ROUTE_IDS,
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
    5: "ec49db18aaaa1f6677d0b1b90ca533543bc4cb26764cefb7bf018feb187f50fa",
    6: "19621b3c3e43a5c7ec652dacd17239c7ffc23dfb32106b667ab8cfa12fcc27f2",
}
FROZEN_CANONICAL_REGISTRY_HASHES = {
    1: "d9c84001420bd63a82418ee3cfe1776895be69936e921aa8c4790a8966aa6913",
    2: "cd6e4147ea639f0c3016e88783afcf090ccd8383b70d6efe314599d3909bfa40",
    3: "a914276d613e970d68f2ccb5799ad7e912c2edd5b47d098cfbb1f109055ad6cf",
    4: "d81276ed9b7482768840ef89980d6cbb81361ca2ff84acee3ab7da7bb67eae7e",
    5: "91ef2dcf75bcc4bce22241466477a99f9e34cbd8ac537974e1017a2e1fe92195",
    6: "532329cad6ce302f9f390f1d726fceee94560114c7fb9b3f6d5e2968486bcdde",
}
FROZEN_NAVIGATION_V1_RAW_HASH = (
    "970a40842ce298945b67bbdd65f4191d8506565de7363324bb79f504e2cdacbd"
)
FROZEN_NAVIGATION_V2_RAW_HASH = (
    "f2d3990cf1c22ab20ec13a047e024b4488fde465a67098da37e915b753fe2048"
)
FROZEN_NAVIGATION_V3_RAW_HASH = (
    "086d9a9dc88466d5274c27d7f9225798686287e0bca438bf0d13a2144642eecd"
)
FROZEN_NAVIGATION_V4_RAW_HASH = (
    "c77a741acddff9ae725d1d23e055ac542f7edb2af01ac5b552624e280b299820"
)
FROZEN_NAVIGATION_V5_RAW_HASH = (
    "7e3c47455d1fd951b81922d65fab47587a6f0bc91941ff3a5cfadf4eade7b2f7"
)
FROZEN_AUDIT_V6_RAW_HASH = (
    "9bfc49b724b3aa0914d66431c37e988c0c67b3efdeffca4003d5d81a4f9bc893"
)


class Phase5FramingRegistryTests(unittest.TestCase):
    def test_v1_through_v6_registry_and_instruction_bytes_remain_frozen(self) -> None:
        constants = {
            1: ROUTE_REGISTRY_V1_HASH,
            2: ROUTE_REGISTRY_V2_HASH,
            3: ROUTE_REGISTRY_V3_HASH,
            4: ROUTE_REGISTRY_V4_HASH,
            5: ROUTE_REGISTRY_V5_HASH,
            6: ROUTE_REGISTRY_V6_HASH,
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
        navigation_v2 = REPOSITORY_ROOT / "machine" / "navigation-registry.v2.json"
        self.assertEqual(
            sha256_digest(navigation_v2.read_bytes()),
            FROZEN_NAVIGATION_V2_RAW_HASH,
        )
        navigation_v3 = REPOSITORY_ROOT / "machine" / "navigation-registry.v3.json"
        self.assertEqual(
            sha256_digest(navigation_v3.read_bytes()),
            FROZEN_NAVIGATION_V3_RAW_HASH,
        )
        navigation_v4 = REPOSITORY_ROOT / "machine" / "navigation-registry.v4.json"
        self.assertEqual(
            sha256_digest(navigation_v4.read_bytes()),
            FROZEN_NAVIGATION_V4_RAW_HASH,
        )
        navigation_v5 = REPOSITORY_ROOT / "machine" / "navigation-registry.v5.json"
        self.assertEqual(
            sha256_digest(navigation_v5.read_bytes()),
            FROZEN_NAVIGATION_V5_RAW_HASH,
        )
        audit_v6 = (
            REPOSITORY_ROOT
            / "routes"
            / "instructions"
            / "audit.framing_economics.v6.txt"
        )
        self.assertEqual(sha256_digest(audit_v6.read_bytes()), FROZEN_AUDIT_V6_RAW_HASH)

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

    def test_v6_advances_only_the_framing_audit_instruction(self) -> None:
        v5 = load_route_registry_by_hash(ROUTE_REGISTRY_V5_HASH)
        v6 = load_route_registry_by_hash(ROUTE_REGISTRY_V6_HASH)
        v5_by_id = {route.route_id: route for route in v5.routes}
        v6_by_id = {route.route_id: route for route in v6.routes}

        self.assertEqual(V6_ROUTE_IDS, V5_ROUTE_IDS)
        self.assertEqual(V6_NATIVE_ROUTE_IDS, frozenset({"audit.framing_economics"}))
        self.assertEqual(V6_ENABLED_ROUTE_IDS, frozenset(V6_ROUTE_IDS))
        self.assertTrue(all(isinstance(route, RouteSpecV6) for route in v6.routes))

        for route_id in V6_ROUTE_IDS:
            old = v5_by_id[route_id]
            active = v6_by_id[route_id]
            if route_id != "audit.framing_economics":
                with self.subTest(frozen_route=route_id):
                    self.assertEqual(
                        active.model_dump(mode="json"), old.model_dump(mode="json")
                    )
                    self.assertEqual(
                        instruction_bundle_bytes(active), instruction_bundle_bytes(old)
                    )
                continue

            old_payload = old.model_dump(mode="json")
            active_payload = active.model_dump(mode="json")
            for field in (
                "instruction_bundle_hash",
                "instruction_bundle_id",
                "route_version",
            ):
                old_payload.pop(field)
                active_payload.pop(field)
            self.assertEqual(active_payload, old_payload)
            self.assertEqual(active.route_version, 6)
            self.assertEqual(
                active.instruction_bundle_id, "audit.framing_economics.v6"
            )
            old_instruction = instruction_bundle_bytes(old)
            active_instruction = instruction_bundle_bytes(active)
            self.assertNotEqual(active_instruction, old_instruction)
            self.assertNotIn(b"active-margin payoff check", old_instruction)
            self.assertIn(b"active-margin payoff check", active_instruction)
            self.assertIn(b"binary action set", active_instruction)
            self.assertIn(b"best feasible deviation", active_instruction)
            self.assertIn(b"continuous choice", active_instruction)
            self.assertIn(
                b"upstream source of this link changes the payoff difference",
                active_instruction,
            )
            self.assertIn(b"classify the margin as unresolved", active_instruction)

    def test_v7_advances_only_the_research_first_framing_audit(self) -> None:
        v6 = load_route_registry_by_hash(ROUTE_REGISTRY_V6_HASH)
        v7 = load_route_registry_by_hash(ROUTE_REGISTRY_V7_HASH)
        v6_by_id = {route.route_id: route for route in v6.routes}
        v7_by_id = {route.route_id: route for route in v7.routes}

        self.assertEqual(V7_ROUTE_IDS, V6_ROUTE_IDS)
        self.assertEqual(V7_NATIVE_ROUTE_IDS, frozenset({"audit.framing_economics"}))
        self.assertEqual(V7_ENABLED_ROUTE_IDS, frozenset(V7_ROUTE_IDS))
        self.assertTrue(all(isinstance(route, RouteSpecV7) for route in v7.routes))

        for route_id in V7_ROUTE_IDS:
            old = v6_by_id[route_id]
            active = v7_by_id[route_id]
            if route_id != "audit.framing_economics":
                self.assertEqual(
                    active.model_dump(mode="json"), old.model_dump(mode="json")
                )
                self.assertEqual(
                    instruction_bundle_bytes(active), instruction_bundle_bytes(old)
                )
                continue
            old_payload = old.model_dump(mode="json")
            active_payload = active.model_dump(mode="json")
            for field in (
                "instruction_bundle_hash",
                "instruction_bundle_id",
                "route_version",
            ):
                old_payload.pop(field)
                active_payload.pop(field)
            self.assertEqual(active_payload, old_payload)
            self.assertEqual(active.route_version, 7)
            self.assertEqual(active.instruction_bundle_id, "audit.framing_economics.v7")
            instruction = instruction_bundle_bytes(active)
            self.assertIn(b"consequence_binding", instruction)
            self.assertIn(b"distinctive mechanism", instruction)

    def test_navigation_contract_admits_first_audit_and_five_input_continuation(self) -> None:
        route = load_route_registry_by_hash(ROUTE_REGISTRY_V8_HASH).routes[-1]
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

    def test_navigation_v7_is_active_while_historical_versions_remain_addressable(self) -> None:
        active_routes = load_route_registry()
        self.assertEqual(active_routes.registry_version, 8)
        self.assertEqual(ROUTE_REGISTRY_HASH, ROUTE_REGISTRY_V8_HASH)
        self.assertEqual(registry_hash(active_routes), ROUTE_REGISTRY_V8_HASH)

        active_navigation = load_navigation_registry()
        self.assertIsInstance(active_navigation, NavigationRegistryV7)
        self.assertEqual(NAVIGATION_REGISTRY_HASH, NAVIGATION_REGISTRY_V7_HASH)
        self.assertEqual(active_navigation.navigation_registry_version, 7)
        self.assertEqual(active_navigation.route_registry_hash, ROUTE_REGISTRY_V8_HASH)
        policy = active_navigation.routes[-1]
        self.assertEqual(policy.route_id, "audit.framing_economics")
        self.assertEqual(policy.route_version, 8)
        self.assertEqual(policy.selector_id, "registry_cardinality.v1")
        self.assertEqual(policy.purpose, "scientific_framing_audit")
        self.assertEqual(policy.default_budget_units, 18000)
        decompose = next(
            item
            for item in active_navigation.routes
            if item.route_id == "decompose.primitives"
        )
        self.assertEqual(
            decompose.selector_id, "uncompleted_decomposition_scope.v1"
        )
        self.assertEqual(decompose.default_budget_units, 8_000)
        specialized = tuple(
            item
            for item in active_navigation.routes
            if item.selector_id == "uncompleted_decomposition_scope.v1"
        )
        self.assertEqual(tuple(item.route_id for item in specialized), ("decompose.primitives",))

        historical = load_navigation_registry_by_hash(NAVIGATION_REGISTRY_V1_HASH)
        self.assertIsInstance(historical, NavigationRegistryV1)
        self.assertEqual(historical.navigation_registry_version, 1)
        self.assertEqual(historical.route_registry_hash, ROUTE_REGISTRY_V4_HASH)
        historical_v2 = load_navigation_registry_by_hash(NAVIGATION_REGISTRY_V2_HASH)
        self.assertIsInstance(historical_v2, NavigationRegistryV2)
        self.assertEqual(historical_v2.navigation_registry_version, 2)
        self.assertEqual(historical_v2.route_registry_hash, ROUTE_REGISTRY_V5_HASH)
        historical_decompose = next(
            item
            for item in historical_v2.routes
            if item.route_id == "decompose.primitives"
        )
        self.assertEqual(historical_decompose.selector_id, "registry_cardinality.v1")
        historical_v3 = load_navigation_registry_by_hash(NAVIGATION_REGISTRY_V3_HASH)
        self.assertIsInstance(historical_v3, NavigationRegistryV3)
        self.assertEqual(historical_v3.navigation_registry_version, 3)
        historical_v3_decompose = next(
            item
            for item in historical_v3.routes
            if item.route_id == "decompose.primitives"
        )
        self.assertEqual(
            historical_v3_decompose.selector_id,
            "uncompleted_decomposition_scope.v1",
        )
        self.assertEqual(historical_v3_decompose.default_budget_units, 4_000)

        historical_v4 = load_navigation_registry_by_hash(NAVIGATION_REGISTRY_V4_HASH)
        self.assertIsInstance(historical_v4, NavigationRegistryV4)
        self.assertEqual(historical_v4.navigation_registry_version, 4)
        self.assertEqual(historical_v4.route_registry_hash, ROUTE_REGISTRY_V5_HASH)
        historical_v5 = load_navigation_registry_by_hash(NAVIGATION_REGISTRY_V5_HASH)
        self.assertIsInstance(historical_v5, NavigationRegistryV5)
        self.assertEqual(historical_v5.navigation_registry_version, 5)
        self.assertEqual(historical_v5.route_registry_hash, ROUTE_REGISTRY_V6_HASH)
        active_as_v5 = active_navigation.model_dump(mode="json")
        active_as_v5["navigation_registry_version"] = 5
        active_as_v5["route_registry_hash"] = ROUTE_REGISTRY_V6_HASH
        for item in active_as_v5["routes"]:
            if item["route_id"] == "audit.framing_economics":
                item["route_version"] = 6
        self.assertEqual(active_as_v5, historical_v5.model_dump(mode="json"))

        v5_as_v4 = historical_v5.model_dump(mode="json")
        v5_as_v4["navigation_registry_version"] = 4
        v5_as_v4["route_registry_hash"] = ROUTE_REGISTRY_V5_HASH
        for item in v5_as_v4["routes"]:
            if item["route_id"] == "audit.framing_economics":
                item["route_version"] = 5
        self.assertEqual(v5_as_v4, historical_v4.model_dump(mode="json"))

        v4_as_v3 = historical_v4.model_dump(mode="json")
        v4_as_v3["navigation_registry_version"] = 3
        for item in v4_as_v3["routes"]:
            if item["route_id"] == "decompose.primitives":
                item["default_budget_units"] = 4_000
        self.assertEqual(v4_as_v3, historical_v3.model_dump(mode="json"))

        v2_payload = historical_v2.model_dump(mode="json")
        v3_payload = historical_v3.model_dump(mode="json")
        v3_payload["navigation_registry_version"] = 2
        for item in v3_payload["routes"]:
            if item["route_id"] == "decompose.primitives":
                item["selector_id"] = "registry_cardinality.v1"
        self.assertEqual(v3_payload, v2_payload)


if __name__ == "__main__":
    unittest.main()
