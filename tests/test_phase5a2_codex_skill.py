from __future__ import annotations

from pathlib import Path
import re
import unittest

from econ_theorist.policy import load_route_registry


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / ".agents" / "skills" / "econ-theorist-v2"


class Phase5A2CodexSkillTests(unittest.TestCase):
    def test_projection_is_thin_and_engine_owned(self) -> None:
        files = {
            path.relative_to(SKILL_ROOT).as_posix()
            for path in SKILL_ROOT.rglob("*")
            if path.is_file()
        }
        self.assertEqual(files, {"SKILL.md", "agents/openai.yaml"})

        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("TODO", text)
        self.assertLessEqual(len(text.splitlines()), 120)
        self.assertIn("etai codex invoke", text)
        self.assertIn("WorkPacket", text)
        self.assertIn("candidate_authoring_contract", text)
        self.assertIn("Do not read package source, tests", text)
        self.assertIn("stop as an engine", text)
        self.assertIn("compatibility error instead of inspecting", text)
        self.assertIn("Keep Phase 5A execution single-agent", text)
        self.assertIn("Only when the bridge returns `team_ready`", text)
        self.assertIn("exact current user turn", text)
        self.assertIn("without replacing them with titles or short summaries", text)
        self.assertIn("`awaiting_choice_review`", text)
        self.assertIn("bounded literature orientation", text)
        self.assertIn("ordinary-agent baseline", text)
        self.assertIn("never novelty or absorption evidence", text)
        self.assertIn("never relabel or select it as a third direction", text)
        self.assertIn("not a fixed research\n  method", text)
        self.assertIn("summarizing it", text)
        self.assertIn("Only `handoff_ready` permits exactly one research worker", text)
        self.assertIn("include the exact handoff hash", text)
        self.assertIn("candidate authoring contract", text)
        self.assertIn("observable agent/model labels", text)
        self.assertIn("Other stops create no worker", text)
        self.assertIn("never pretend", text)
        self.assertIn("Do not choose or reorder routes yourself", text)
        self.assertIn("Omit both", text)
        self.assertIn("on every ordinary continuation", text)
        self.assertIn("rather than replaying the old framing", text)
        self.assertIn("Submit a bridge `finish` request", text)
        self.assertIn("exhausted declared retries", text)
        self.assertIn("explicit user cancellation", text)
        self.assertIn("abnormal host/model abort", text)
        self.assertIn("Do not finish an ordinary human wait", text)
        self.assertIn("Do not use `finish` as a generic pause", text)
        self.assertIn("Do not rewrite `run.json`", text)
        for required_guardrail in (
            "Freeze each\n   intended field separately",
            "write the request as UTF-8, re-read it",
            "Preserve the user's framing text",
            "do not make\n   the two fields identical",
            "`WorkPacket.run_input`",
            "neutral `project_name`",
            "clean-context sealed lanes",
            "no inherited\n  coordinator/task turns",
            "Capability labels authorize host operations only",
            "Hashes, status, paths, or report links alone are\n  not delivery",
        ):
            self.assertIn(required_guardrail, text)

        for route in load_route_registry().routes:
            self.assertNotIn(route.route_id, text)
        for copied_rule in (
            "state one falsifiable economic question",
            "minimum-cardinality set cover",
            "validated argument package",
        ):
            self.assertNotIn(copied_rule, text.lower())

    def test_frontmatter_has_bounded_trigger_and_exclusions(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"---\n(.*?)\n---\n", text, flags=re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)  # type: ignore[union-attr]
        self.assertIn("name: econ-theorist-v2", frontmatter)
        self.assertIn("explicitly asks to initialize", frontmatter)
        self.assertIn("already v2-bound", frontmatter)
        self.assertIn("Do not use for empirical, econometric", frontmatter)

    def test_openai_metadata_can_trigger_explicitly_or_implicitly(self) -> None:
        text = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn('display_name: "Econ Theorist AI v2"', text)
        self.assertIn("$econ-theorist-v2", text)
        self.assertIn("allow_implicit_invocation: true", text)
        match = re.search(r'short_description: "([^"]+)"', text)
        self.assertIsNotNone(match)
        description = match.group(1)  # type: ignore[union-attr]
        self.assertGreaterEqual(len(description), 25)
        self.assertLessEqual(len(description), 64)


if __name__ == "__main__":
    unittest.main()
