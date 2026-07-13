from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.machine.authority import (
    ApprovalError,
    HmacTrustedHumanChannel,
    confirm_decision_with_receipt,
    create_human_approval_challenge,
    record_approval_issued,
)
from econ_theorist.machine.binding import bind_or_initialize_project
from econ_theorist.machine.egress import (
    EgressError,
    HmacTrustedEgressChannel,
    create_egress_plan,
    deliver_work_packet,
    record_egress_authorization_issued,
)
from econ_theorist.machine.models import (
    CapabilityV1,
    CapabilityReceiptV1,
    DiscoveryGrantV1,
    RunInputBriefV1,
)
from econ_theorist.machine.navigation import plan_next
from econ_theorist.machine.operational import ProjectOperationalLayout
from econ_theorist.machine.packets import read_work_packet
from econ_theorist.machine.run_service import open_or_resume_run
from econ_theorist.models import Actor, Decision
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


class Phase5AAuthorityEgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        self.local_home = self.anchor / "local-home"
        grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
        )
        bind_or_initialize_project(
            self.root,
            discovery_grant=grant,
            initialize=True,
            project_name="Authority and egress test",
            actor_id="human.owner",
            operation_key="initialize.authority",
            reserved_at="2026-07-13T00:00:00Z",
            operational_home=self.local_home,
        )
        self.layout = StoreLayout.at(self.root)
        self.operational = ProjectOperationalLayout.at(self.layout)

    def _open_packet(self):
        snapshot = replay(self.layout)
        actor = Actor(kind="agent", actor_id="scientific_writer")
        brief = RunInputBriefV1(
            project_id=snapshot.project_id,
            base_head=snapshot.head,
            requested_scope="Frame one public test question.",
            framing_intent="What is the economic mechanism in this bounded fixture?",
            privacy="project_private",
            compartments=("project_research",),
            actor_role=actor.actor_id,
        )
        plan = plan_next(
            self.layout,
            snapshot,
            actor=actor,
            compartments=("project_research",),
            privacy_clearance="project_private",
            budget_units=10_000,
            run_input_brief=brief,
        )
        self.assertEqual(plan.outcome, "unique_next")
        opened = open_or_resume_run(
            self.layout,
            operation_key="open.egress.fixture",
            reserved_at="2026-07-13T00:00:01Z",
            candidate=plan.candidates[0],
            run_input_brief=brief,
            operational=self.operational,
        )
        packet = read_work_packet(
            self.operational, opened.route_run_id, opened.work_packet_hash
        )
        return opened, packet

    def test_trusted_receipt_is_single_use_and_commits_exact_decision(self) -> None:
        snapshot = replay(self.layout)
        decision = Decision(
            decision_id="decision.theory.mode",
            version=1,
            project_id=snapshot.project_id,
            decision_kind="theory_mode",
            subject_ref=snapshot.project_id,
            question="Use applied theory mode?",
            options=("applied", "foundational"),
            selected_option="applied",
            recommendation="applied",
            rationale="Direct human choice for the authority fixture.",
            required_authority="L2",
            decider=Actor(kind="human", actor_id="human.owner"),
            decided_at="2026-07-13T00:00:02Z",
            status="confirmed",
        )
        challenge = create_human_approval_challenge(
            decision,
            head=snapshot.head,
            blast_radius_summary="Activates one exact theory-mode Decision.",
            expires_at="2026-07-14T00:00:00Z",
            challenge_id="approval.challenge.test",
        )
        channel = HmacTrustedHumanChannel("trusted.test", b"h" * 32)
        with self.assertRaises(ApprovalError):
            channel.issue(
                challenge,
                direct_user_gesture=False,
                issued_at="2026-07-13T00:00:03Z",
                nonce="denied",
            )
        receipt = channel.issue(
            challenge,
            direct_user_gesture=True,
            issued_at="2026-07-13T00:00:03Z",
            nonce="trusted-user-nonce",
        )
        record_approval_issued(self.operational, challenge, receipt, channel)
        request_digest = sha256_digest(
            canonical_json_bytes({"decision": decision, "receipt": receipt})
        )
        result = confirm_decision_with_receipt(
            self.layout,
            self.operational,
            operation_key="confirm.theory.mode",
            request_digest=request_digest,
            decision=decision,
            challenge=challenge,
            receipt=receipt,
            channel=channel,
            now="2026-07-13T00:00:04Z",
        )
        self.assertEqual(result.status, "committed")
        self.assertIn(decision, replay(self.layout).decisions)
        recovered = confirm_decision_with_receipt(
            self.layout,
            self.operational,
            operation_key="confirm.theory.mode",
            request_digest=request_digest,
            decision=decision,
            challenge=challenge,
            receipt=receipt,
            channel=channel,
            now="2026-07-13T00:00:05Z",
        )
        self.assertEqual(recovered.status, "already_committed")
        with self.assertRaises(ApprovalError):
            confirm_decision_with_receipt(
                self.layout,
                self.operational,
                operation_key="second.spend",
                request_digest=request_digest,
                decision=decision,
                challenge=challenge,
                receipt=receipt,
                channel=channel,
                now="2026-07-13T00:00:06Z",
            )
        forged = receipt.model_copy(update={"selected_option": "foundational"})
        with self.assertRaises(ApprovalError):
            channel.verify(forged)

    def test_provider_delivery_starts_durably_and_never_auto_retries(self) -> None:
        opened, packet = self._open_packet()
        capability = CapabilityReceiptV1(
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            adapter_version="1.0",
            execution_class="provider_backed",
            technically_accessible_roots=(str(self.root),),
            model_tool_isolation="verified",
            trusted_human_channel="verified",
            environment_redaction="verified",
            credential_store_isolation="verified",
            secret_file_denial="verified",
            shadow_workspace_isolation="verified",
            capabilities=_required_capabilities(),
            observed_at="2026-07-13T00:00:02Z",
        )
        plan = create_egress_plan(
            packet,
            capability,
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            provider="provider.test",
            model="model.test",
            execution_class="provider_backed",
            retention="no_training_30_day_logs",
            training_use="disabled",
            logging="bounded",
            region="test-region",
            human_review="disabled",
        )
        blocked = deliver_work_packet(
            self.layout,
            self.operational,
            route_run_id=opened.route_run_id,
            packet_hash=opened.work_packet_hash,
            operation_key="delivery.test",
            request_digest="d" * 64,
            plan=plan,
            capability=capability,
            host_session_id="session.test",
            adapter_version="1.0",
            delivery_time="2026-07-13T00:00:03Z",
        )
        self.assertEqual(blocked.status, "blocked_before_delivery")
        self.assertIsNone(blocked.work_packet)

        channel = HmacTrustedEgressChannel("egress.test", b"e" * 32)
        authorization = channel.issue(
            plan,
            direct_user_gesture=True,
            expires_at="2026-07-14T00:00:00Z",
            issued_at="2026-07-13T00:00:03Z",
            nonce="egress-user-nonce",
        )
        record_egress_authorization_issued(
            self.operational, plan, authorization, channel
        )
        delivered = deliver_work_packet(
            self.layout,
            self.operational,
            route_run_id=opened.route_run_id,
            packet_hash=opened.work_packet_hash,
            operation_key="delivery.test",
            request_digest="d" * 64,
            plan=plan,
            capability=capability,
            host_session_id="session.test",
            adapter_version="1.0",
            delivery_time="2026-07-13T00:00:04Z",
            authorization=authorization,
            channel=channel,
        )
        self.assertEqual(delivered.status, "delivery_started")
        self.assertEqual(delivered.work_packet, packet)

        retry = deliver_work_packet(
            self.layout,
            self.operational,
            route_run_id=opened.route_run_id,
            packet_hash=opened.work_packet_hash,
            operation_key="delivery.test",
            request_digest="d" * 64,
            plan=plan,
            capability=capability,
            host_session_id="session.test",
            adapter_version="1.0",
            delivery_time="2026-07-13T00:00:04Z",
            authorization=authorization,
            channel=channel,
        )
        self.assertEqual(retry.status, "unknown_possible_egress")
        self.assertIsNone(retry.work_packet)

    def test_local_only_packet_cannot_receive_provider_plan(self) -> None:
        _, packet = self._open_packet()
        local_only = packet.model_copy(update={"privacy_clearance": "local_only"})
        capability = CapabilityReceiptV1(
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            adapter_version="1.0",
            execution_class="provider_backed",
            technically_accessible_roots=(str(self.root),),
            model_tool_isolation="verified",
            trusted_human_channel="verified",
            environment_redaction="verified",
            credential_store_isolation="verified",
            secret_file_denial="verified",
            shadow_workspace_isolation="verified",
            capabilities=_required_capabilities(),
            observed_at="2026-07-13T00:00:02Z",
        )
        with self.assertRaises(EgressError):
            create_egress_plan(
                local_only,
                capability,
                host_product="test-host",
                host_version="1.0",
                adapter_id="generic.test",
                provider="provider.test",
                model="model.test",
                execution_class="provider_backed",
            )

    def test_bounded_reuse_has_an_exact_limit_and_same_key_never_retries(self) -> None:
        opened, packet = self._open_packet()
        capability = CapabilityReceiptV1(
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            adapter_version="1.0",
            execution_class="provider_backed",
            technically_accessible_roots=(str(self.root),),
            model_tool_isolation="verified",
            trusted_human_channel="verified",
            environment_redaction="verified",
            credential_store_isolation="verified",
            secret_file_denial="verified",
            shadow_workspace_isolation="verified",
            capabilities=_required_capabilities(),
            observed_at="2026-07-13T00:00:02Z",
        )
        plan = create_egress_plan(
            packet,
            capability,
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            provider="provider.test",
            model="model.test",
            execution_class="provider_backed",
            retention="bounded",
            training_use="disabled",
            logging="bounded",
            region="test-region",
            human_review="disabled",
        )
        channel = HmacTrustedEgressChannel("egress.bound", b"b" * 32)
        with self.assertRaises(EgressError):
            channel.issue(
                plan,
                direct_user_gesture=True,
                reuse="bounded_reuse",
                expires_at="2026-07-14T00:00:00Z",
            )
        authorization = channel.issue(
            plan,
            direct_user_gesture=True,
            reuse="bounded_reuse",
            max_deliveries=2,
            expires_at="2026-07-14T00:00:00Z",
            issued_at="2026-07-13T00:00:03Z",
            nonce="bounded-user-nonce",
        )
        record_egress_authorization_issued(
            self.operational, plan, authorization, channel
        )

        def deliver(key: str, second: int):
            return deliver_work_packet(
                self.layout,
                self.operational,
                route_run_id=opened.route_run_id,
                packet_hash=opened.work_packet_hash,
                operation_key=key,
                request_digest=str(second) * 64,
                plan=plan,
                capability=capability,
                host_session_id=f"session.{second}",
                adapter_version="1.0",
                delivery_time=f"2026-07-13T00:00:0{second}Z",
                authorization=authorization,
                channel=channel,
            )

        self.assertEqual(deliver("delivery.bound.one", 4).status, "delivery_started")
        retry = deliver("delivery.bound.one", 5)
        self.assertEqual(retry.status, "unknown_possible_egress")
        self.assertIsNone(retry.work_packet)
        self.assertEqual(deliver("delivery.bound.two", 6).status, "delivery_started")
        with self.assertRaises(EgressError):
            deliver("delivery.bound.three", 7)


if __name__ == "__main__":
    unittest.main()
