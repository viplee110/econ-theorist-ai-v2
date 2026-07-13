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
        self.assertLessEqual(len(text.splitlines()), 100)
        self.assertIn("etai codex invoke", text)
        self.assertIn("WorkPacket", text)
        self.assertIn("candidate_authoring_contract", text)
        self.assertIn("Do not read package source, tests", text)
        self.assertIn("stop as an engine", text)
        self.assertIn("compatibility error instead of inspecting", text)
        self.assertIn("Keep Phase 5A execution single-agent", text)
        self.assertIn("Do not choose or reorder routes yourself", text)

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
