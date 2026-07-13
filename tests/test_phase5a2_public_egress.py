from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.machine.binding import bind_or_initialize_project
from econ_theorist.machine.dispatcher import MachineDispatcher
from econ_theorist.machine.egress import (
    EgressError,
    _events,
    create_egress_plan,
    deliver_work_packet,
)
from econ_theorist.machine.models import (
    CapabilityReceiptV1,
    CapabilityV1,
    DeliveryEnvelopeV1,
    DiscoveryGrantV1,
    EgressPlanV1,
    MachineRequestV1,
    RunInputBriefV1,
)
from econ_theorist.machine.navigation import plan_next
from econ_theorist.machine.operational import (
    ContentAddressedOperationalStore,
    ProjectOperationalLayout,
)
from econ_theorist.machine.packets import read_work_packet
from econ_theorist.machine.run_service import open_or_resume_run
from econ_theorist.models import Actor
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.replay import replay


def _required_capabilities() -> tuple[CapabilityV1, ...]:
    return tuple(
        CapabilityV1(
            capability_id=identifier,
            available=True,
            required=True,
            evidence="trusted test adapter",
        )
        for identifier in (
            "python_runtime",
            "structured_process_invocation",
            "single_agent_topology",
        )
    )


class Phase5A2PublicEgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        self.grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
        )
        bind_or_initialize_project(
            self.root,
            discovery_grant=self.grant,
            initialize=True,
            project_name="Public provider egress test",
            project_privacy="public",
            actor_id="human.owner",
            operation_key="initialize.public.egress",
            reserved_at="2026-07-14T00:00:00Z",
            operational_home=self.anchor / "local-home",
        )
        self.layout = StoreLayout.at(self.root)
        self.operational = ProjectOperationalLayout.at(self.layout)

    def _open_packet(self, privacy: str = "public"):
        snapshot = replay(self.layout)
        actor = Actor(kind="agent", actor_id="scientific_writer")
        brief = RunInputBriefV1(
            project_id=snapshot.project_id,
            base_head=snapshot.head,
            requested_scope="Frame one public test question.",
            framing_intent="Identify the economic mechanism in this fixture.",
            privacy=privacy,
            compartments=("project_research",),
            actor_role=actor.actor_id,
        )
        navigation = plan_next(
            self.layout,
            snapshot,
            actor=actor,
            compartments=("project_research",),
            privacy_clearance=privacy,
            budget_units=10_000,
            run_input_brief=brief,
        )
        self.assertEqual(navigation.outcome, "unique_next")
        opened = open_or_resume_run(
            self.layout,
            operation_key="open.public.egress.fixture",
            reserved_at="2026-07-14T00:00:01Z",
            candidate=navigation.candidates[0],
            run_input_brief=brief,
            operational=self.operational,
        )
        packet = read_work_packet(
            self.operational, opened.route_run_id, opened.work_packet_hash
        )
        return opened, opened.work_packet_hash, packet

    def _capability(self, *, verified: bool) -> CapabilityReceiptV1:
        if verified:
            observations = ("verified",) * 6
        else:
            observations = (
                "unverified",
                "unavailable",
                "unverified",
                "unavailable",
                "unverified",
                "unavailable",
            )
        return CapabilityReceiptV1(
            host_product="codex",
            host_version="test",
            adapter_id="codex.project-skill",
            adapter_version="1.0",
            execution_class="provider_backed",
            technically_accessible_roots=(str(self.root),),
            model_tool_isolation=observations[0],
            trusted_human_channel=observations[1],
            environment_redaction=observations[2],
            credential_store_isolation=observations[3],
            secret_file_denial=observations[4],
            shadow_workspace_isolation=observations[5],
            capabilities=_required_capabilities(),
            observed_at="2026-07-14T00:00:02Z",
        )

    def _plan(self, packet, capability: CapabilityReceiptV1) -> EgressPlanV1:
        return create_egress_plan(
            packet,
            capability,
            host_product="codex",
            host_version="test",
            adapter_id="codex.project-skill",
            provider="openai",
            model="provider-selected",
            execution_class="provider_backed",
        )

    def test_public_provider_delivery_needs_no_authorization_and_never_retries(
        self,
    ) -> None:
        opened, packet_hash, packet = self._open_packet()
        capability = self._capability(verified=False)
        plan = self._plan(packet, capability)

        self.assertEqual(plan.execution_class, "provider_backed")
        self.assertEqual(plan.privacy_labels, ("public",))
        self.assertFalse(plan.authorization_required)
        delivered = deliver_work_packet(
            self.layout,
            self.operational,
            route_run_id=opened.route_run_id,
            packet_hash=packet_hash,
            operation_key="delivery.public.provider",
            request_digest="a" * 64,
            plan=plan,
            capability=capability,
            host_session_id="session.public",
            adapter_version="1.0",
            delivery_time="2026-07-14T00:00:03Z",
        )
        self.assertEqual(delivered.status, "delivery_started")
        self.assertEqual(delivered.work_packet, packet)

        store = ContentAddressedOperationalStore(
            self.operational.project_root,
            self.operational.runs / opened.route_run_id,
        )
        envelope = DeliveryEnvelopeV1.model_validate_json(
            store.read_bytes("envelopes", delivered.delivery_envelope_hash),
            strict=True,
        )
        self.assertEqual(envelope.pre_delivery_status, "authorized_to_deliver")
        self.assertIsNone(envelope.egress_authorization_hash)
        self.assertIsNotNone(envelope.egress_plan_hash)
        stored_plan = EgressPlanV1.model_validate_json(
            store.read_bytes("egress-plans", envelope.egress_plan_hash),
            strict=True,
        )
        self.assertEqual(stored_plan, plan)
        self.assertEqual(stored_plan.execution_class, "provider_backed")

        subject_id = "public_" + sha256_digest(
            canonical_json_bytes(plan)
        )[:48]
        events = _events(self.operational, subject_id)
        self.assertEqual(events[0][1].event, "public_plan_registered")
        self.assertEqual(events[-1][1].event, "delivery_started")
        self.assertFalse(
            any(
                path.name.startswith("local_")
                for path in self.operational.egress.iterdir()
            )
        )

        retry = deliver_work_packet(
            self.layout,
            self.operational,
            route_run_id=opened.route_run_id,
            packet_hash=packet_hash,
            operation_key="delivery.public.provider",
            request_digest="a" * 64,
            plan=plan,
            capability=capability,
            host_session_id="session.public",
            adapter_version="1.0",
            delivery_time="2026-07-14T00:00:04Z",
        )
        self.assertEqual(retry.status, "unknown_possible_egress")
        self.assertEqual(
            retry.delivery_envelope_hash, delivered.delivery_envelope_hash
        )
        self.assertIsNone(retry.work_packet)

    def test_private_provider_still_requires_verified_controls_and_authorization(
        self,
    ) -> None:
        opened, packet_hash, packet = self._open_packet("project_private")
        with self.assertRaises(EgressError):
            self._plan(packet, self._capability(verified=False))

        capability = self._capability(verified=True)
        plan = self._plan(packet, capability)
        self.assertTrue(plan.authorization_required)
        blocked = deliver_work_packet(
            self.layout,
            self.operational,
            route_run_id=opened.route_run_id,
            packet_hash=packet_hash,
            operation_key="delivery.private.provider",
            request_digest="b" * 64,
            plan=plan,
            capability=capability,
            host_session_id="session.private",
            adapter_version="1.0",
            delivery_time="2026-07-14T00:00:03Z",
        )
        self.assertEqual(blocked.status, "blocked_before_delivery")
        self.assertIsNone(blocked.work_packet)

    def test_unbound_public_copy_is_rejected_by_plan_and_delivery(self) -> None:
        opened, _, private_packet = self._open_packet("project_private")
        assert private_packet.run_input is not None
        public_brief = private_packet.run_input.model_copy(
            update={"privacy": "public"}
        )
        forged_packet = private_packet.model_copy(
            update={
                "privacy_clearance": "public",
                "run_input": public_brief,
                "run_input_brief_hash": sha256_digest(
                    canonical_json_bytes(public_brief)
                ),
            }
        )
        store = ContentAddressedOperationalStore(
            self.operational.project_root,
            self.operational.runs / opened.route_run_id,
        )
        forged_hash, _ = store.install("packets", forged_packet)
        self.assertNotEqual(forged_hash, opened.work_packet_hash)

        capability = self._capability(verified=False)
        forged_plan = self._plan(forged_packet, capability)
        plan_response = MachineDispatcher().dispatch(
            MachineRequestV1(
                operation="egress.plan",
                project_root=str(self.root),
                discovery_grant=self.grant,
                parameters={
                    "route_run_id": opened.route_run_id,
                    "work_packet_hash": forged_hash,
                    "capability": capability.model_dump(mode="json"),
                    "host_product": "codex",
                    "host_version": "test",
                    "adapter_id": "codex.project-skill",
                    "provider": "openai",
                    "model": "provider-selected",
                    "execution_class": "provider_backed",
                },
            )
        )
        self.assertEqual(plan_response.outcome, "error", plan_response)
        self.assertIn(
            "exact active run binding", plan_response.diagnostics[0].message
        )

        with self.assertRaisesRegex(EgressError, "exact active run binding"):
            deliver_work_packet(
                self.layout,
                self.operational,
                route_run_id=opened.route_run_id,
                packet_hash=forged_hash,
                operation_key="delivery.forged.public",
                request_digest="c" * 64,
                plan=forged_plan,
                capability=capability,
                host_session_id="session.forged",
                adapter_version="1.0",
                delivery_time="2026-07-14T00:00:03Z",
            )

    def test_local_only_and_hidden_packets_cannot_use_public_provider_bypass(
        self,
    ) -> None:
        _, _, packet = self._open_packet()
        capability = self._capability(verified=False)
        local_only = packet.model_copy(update={"privacy_clearance": "local_only"})
        with self.assertRaises(EgressError):
            self._plan(local_only, capability)

        hidden = packet.model_copy(
            update={"hidden_compartments": ("blind_reference",)}
        )
        with self.assertRaises(EgressError):
            self._plan(hidden, capability)


if __name__ == "__main__":
    unittest.main()
