"""Focused engine integration checks for the explicit ResearchMove pilot."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_context_runs import HEAD, make_entity

from econ_theorist.codex_bridge import (
    CodexDirectUserCaptureV1,
    CodexSessionV1,
    CodexStartRequestV1,
    CodexTerminalFailureReframeV1,
)
from econ_theorist.context import ContextCompilationError, compile_context
from econ_theorist.models import Actor, EntityVersionRef, RelationVersion, Snapshot
from econ_theorist.policy import (
    SELECTOR_VERSION_RESEARCH_MOVE_PILOT,
    selector_version_for_new_navigation,
    selector_version_is_supported,
)
from econ_theorist.research_craft_pilot import (
    build_research_move_pilot_material,
    research_move_pilot_work_packet_payload,
)
from econ_theorist.route_registry import get_route


ACTOR = Actor(kind="agent", actor_id="scientific_agent")
NOW = "2026-08-01T00:00:00Z"
V4_PATH = (REPOSITORY_ROOT / "craft" / "research_corpus.v4.json").resolve()


def reframe_snapshot() -> Snapshot:
    project = make_entity("project.pilot", "Project", privacy="public")
    question = make_entity(
        "question.pilot", "ResearchQuestion", privacy="public"
    )
    benchmark = make_entity(
        "benchmark.pilot", "BenchmarkSet", privacy="public"
    )
    question_ref = EntityVersionRef(
        entity_id=question.entity_id, version=question.version
    )
    benchmark_ref = EntityVersionRef(
        entity_id=benchmark.entity_id, version=benchmark.version
    )
    relations = (
        RelationVersion(
            relation_id="relation.pilot.frames",
            relation_type="frames",
            version=1,
            project_id=question.project_id,
            source=question_ref,
            target=benchmark_ref,
            dependency_mode="trace_only",
            privacy="public",
            access_compartments=("project_research",),
            created_at=NOW,
        ),
        RelationVersion(
            relation_id="relation.pilot.delta",
            relation_type="benchmark_delta",
            version=1,
            project_id=question.project_id,
            source=benchmark_ref,
            target=question_ref,
            dependency_mode="trace_only",
            privacy="public",
            access_compartments=("project_research",),
            created_at=NOW,
        ),
    )
    entities = (project, question, benchmark)
    return Snapshot(
        project_id=question.project_id,
        head=HEAD,
        chain=(HEAD,),
        entity_versions=entities,
        relation_versions=relations,
        current_entities={item.entity_id: item.version for item in entities},
        current_relations={item.relation_id: item.version for item in relations},
    )


class ResearchMovePilotIntegrationTests(unittest.TestCase):
    def test_selector_is_supported_but_never_default(self) -> None:
        framing = get_route("frame.question_and_benchmarks")
        decomposition = get_route("decompose.primitives")
        self.assertTrue(
            selector_version_is_supported(
                framing, SELECTOR_VERSION_RESEARCH_MOVE_PILOT
            )
        )
        self.assertFalse(
            selector_version_is_supported(
                decomposition, SELECTOR_VERSION_RESEARCH_MOVE_PILOT
            )
        )
        self.assertNotEqual(
            selector_version_for_new_navigation(framing),
            SELECTOR_VERSION_RESEARCH_MOVE_PILOT,
        )

    def test_pilot_compiles_inside_exact_context_and_legacy_bytes_stay_clean(
        self,
    ) -> None:
        snapshot = reframe_snapshot()
        route = get_route("frame.question_and_benchmarks")
        common = dict(
            route=route,
            actor=ACTOR,
            purpose="research_framing",
            compartments=("project_research",),
            privacy_clearance="public",
            focus_entity_ids=(),
            budget_units=10_000,
        )
        legacy = compile_context(snapshot, **common)
        pilot = compile_context(
            snapshot,
            selector_version=SELECTOR_VERSION_RESEARCH_MOVE_PILOT,
            **common,
        )

        self.assertNotIn("research_move_pilot", legacy.payload)
        self.assertEqual(legacy, compile_context(snapshot, **common))
        payload = pilot.payload["research_move_pilot"]
        self.assertEqual(
            set(payload), {"pilot_schema", "provenance", "model_visible"}
        )
        selected_types = {
            item["entity_type"] for item in pilot.payload["entities"]
        }
        self.assertTrue(
            {"ResearchQuestion", "BenchmarkSet"}.issubset(selected_types)
        )
        self.assertEqual(
            payload,
            research_move_pilot_work_packet_payload(
                build_research_move_pilot_material(
                    V4_PATH,
                    route_id="frame.question_and_benchmarks",
                )
            ),
        )

    def test_fresh_frame_and_wrong_route_fail_closed(self) -> None:
        route = get_route("frame.question_and_benchmarks")
        project = make_entity("project.fresh", "Project", privacy="public")
        fresh = Snapshot(
            project_id=project.project_id,
            head=HEAD,
            chain=(HEAD,),
            entity_versions=(project,),
            current_entities={project.entity_id: project.version},
        )
        with self.assertRaisesRegex(ContextCompilationError, "cannot create a fresh"):
            compile_context(
                fresh,
                route=route,
                actor=ACTOR,
                purpose="research_framing",
                compartments=("project_research",),
                privacy_clearance="public",
                focus_entity_ids=(),
                budget_units=10_000,
                selector_version=SELECTOR_VERSION_RESEARCH_MOVE_PILOT,
            )

    def test_start_opt_in_is_explicit_and_old_serialization_is_unchanged(self) -> None:
        session = CodexSessionV1(
            session_id="pilot-session",
            selected_model="gpt-5",
            installed_models=("gpt-5",),
            observed_at=NOW,
        )
        ordinary = CodexStartRequestV1(
            project_root="C:/tmp/pilot",
            requested_scope="Revise an existing framing question.",
            framing_intent="Preserve the tension and test ordinary absorption.",
            session=session,
        )
        self.assertNotIn("research_move_pilot", ordinary.model_dump(mode="json"))
        explicit_null = CodexStartRequestV1(
            project_root=ordinary.project_root,
            requested_scope=ordinary.requested_scope,
            framing_intent=ordinary.framing_intent,
            terminal_reframe=None,
            research_move_pilot=None,
            session=session,
        )
        self.assertEqual(
            explicit_null.model_dump(mode="json"),
            ordinary.model_dump(mode="json"),
        )
        opted_in = CodexStartRequestV1(
            project_root=ordinary.project_root,
            requested_scope=ordinary.requested_scope,
            framing_intent=ordinary.framing_intent,
            session=session,
            terminal_reframe=CodexTerminalFailureReframeV1(
                source_route_run_id="run.audit.failed",
                source_host_receipt_hash="a" * 64,
                capture=CodexDirectUserCaptureV1(
                    session_id=session.session_id,
                    researcher_id="researcher",
                    captured_at=NOW,
                    text="Continue with the explicit reframe pilot.",
                ),
            ),
            research_move_pilot="research_move_pilot.v1",
        )
        self.assertEqual(
            opted_in.model_dump(mode="json")["research_move_pilot"],
            "research_move_pilot.v1",
        )
        with self.assertRaisesRegex(ValueError, "terminal_reframe binding"):
            CodexStartRequestV1(
                project_root="C:/tmp/pilot",
                research_move_pilot="research_move_pilot.v1",
                session=session,
            )


if __name__ == "__main__":
    unittest.main()
