from __future__ import annotations

import base64
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from econ_theorist.codec import canonical_json_bytes
from econ_theorist.compatibility import probe_project_root
from econ_theorist.decisions import commit_decision
from econ_theorist.models import Actor, Decision
from econ_theorist.project import init_project
from econ_theorist.runtime import HeadStore, StoreLayout
from tests.helpers import REPOSITORY_ROOT


def _is_reparse(metadata: os.stat_result) -> bool:
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & flag)


def _tree_snapshot(anchor: Path) -> tuple[tuple[str, str, bytes | str | None], ...]:
    """Capture exact paths, entry kinds, file bytes, and link targets."""

    try:
        root_metadata = anchor.lstat()
    except FileNotFoundError:
        return ()
    records: list[tuple[str, str, bytes | str | None]] = []
    if not stat.S_ISDIR(root_metadata.st_mode) or _is_reparse(root_metadata):
        kind = "reparse" if _is_reparse(root_metadata) else "file"
        value: bytes | str | None
        if kind == "file":
            value = anchor.read_bytes()
        else:
            try:
                value = os.readlink(anchor)
            except OSError:
                value = None
        return ((".", kind, value),)

    pending = [anchor]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as iterator:
            entries = list(iterator)
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(anchor).as_posix()
            metadata = entry.stat(follow_symlinks=False)
            if _is_reparse(metadata):
                try:
                    target: str | None = os.readlink(path)
                except OSError:
                    target = None
                records.append((relative, "reparse", target))
            elif stat.S_ISDIR(metadata.st_mode):
                records.append((relative, "directory", None))
                pending.append(path)
            elif stat.S_ISREG(metadata.st_mode):
                records.append((relative, "file", path.read_bytes()))
            else:
                records.append((relative, "special", None))
    return tuple(sorted(records))


class CompatibilityProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.anchor = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _assert_probe_preserves(
        self,
        root: Path,
        expected: str,
        **kwargs: str,
    ):
        before = _tree_snapshot(self.anchor)
        result = probe_project_root(root, **kwargs)
        after = _tree_snapshot(self.anchor)
        self.assertEqual(result.classification, expected)
        self.assertEqual(after, before)
        return result

    def _new_root(self, name: str) -> Path:
        root = self.anchor / name
        root.mkdir()
        return root

    def _initialized(self, name: str, *, with_decision: bool = False):
        root = self._new_root(name)
        snapshot = init_project(root, name=name, actor_id="human.owner")
        if with_decision:
            decision = Decision(
                decision_id=f"decision.{name}",
                version=1,
                project_id=snapshot.project_id,
                decision_kind="G1_question_benchmark",
                subject_ref=snapshot.project_id,
                question="Confirm the exact current research base?",
                options=("confirm", "revise"),
                selected_option="confirm",
                recommendation="confirm",
                rationale="Focused compatibility-probe chain fixture.",
                required_authority="L2",
                decider=Actor(kind="human", actor_id="human.owner"),
                decided_at="2026-07-13T00:00:00Z",
                status="confirmed",
            )
            commit_decision(StoreLayout.at(root), decision)
        return root, snapshot

    def _head_payload(self, root: Path) -> tuple[dict[str, object], str]:
        layout = StoreLayout.at(root)
        head = HeadStore(layout).read()
        assert head is not None
        path = layout.transactions_root / head
        return json.loads(path.read_text(encoding="utf-8")), head

    def _install_head_payload(self, root: Path, payload: dict[str, object]) -> str:
        layout = StoreLayout.at(root)
        data = canonical_json_bytes(payload)
        digest = hashlib.sha256(data).hexdigest()
        target = layout.transactions_root / digest
        target.write_bytes(data)
        layout.main_ref.write_bytes(digest.encode("ascii"))
        return digest

    def test_absent_root_or_store_is_observed_without_creation(self) -> None:
        existing = self._new_root("no-store")
        missing = self.anchor / "missing-root"
        existing_result = self._assert_probe_preserves(existing, "absent")
        missing_result = self._assert_probe_preserves(missing, "absent")
        self.assertIn("store_absent", existing_result.diagnostics)
        self.assertIn("project_root_absent", missing_result.diagnostics)
        self.assertFalse(missing.exists())

    def test_empty_store_and_only_empty_engine_directories_are_virgin(self) -> None:
        empty = self._new_root("empty-store")
        (empty / ".econ-theorist").mkdir()
        skeleton = self._new_root("empty-skeleton")
        StoreLayout.at(skeleton).ensure()

        self._assert_probe_preserves(empty, "virgin")
        self._assert_probe_preserves(skeleton, "virgin")

    def test_unknown_empty_directory_is_not_silently_treated_as_virgin(self) -> None:
        root = self._new_root("unknown-empty")
        (root / ".econ-theorist" / "unknown-owner").mkdir(parents=True)
        result = self._assert_probe_preserves(root, "recovery_required")
        self.assertIn("headless_store_residue", result.diagnostics)

    def test_every_headless_residue_family_requires_recovery(self) -> None:
        residues = {
            "config": ("project.json", b"{}"),
            "transaction": ("transactions/sha256/" + "a" * 64, b"{}"),
            "artifact": ("artifacts/sha256/" + "b" * 64, b"artifact"),
            "provenance": ("provenance/sha256/" + "c" * 64, b"provenance"),
            "run": ("runs/run.one/run.json", b"{}"),
            "staging": ("staging/run.one/candidate.json", b"{}"),
            "lock": ("locks/commit", b"\0"),
            "orphan": ("orphan.bin", b"orphan"),
        }
        for name, (relative, data) in residues.items():
            with self.subTest(name=name):
                root = self._new_root(f"residue-{name}")
                target = root / ".econ-theorist" / relative
                target.parent.mkdir(parents=True)
                target.write_bytes(data)
                self._assert_probe_preserves(root, "recovery_required")

    def test_current_two_transaction_chain_is_valid_and_calls_no_mutator(self) -> None:
        root, snapshot = self._initialized("valid-chain", with_decision=True)
        before = _tree_snapshot(self.anchor)
        forbidden = AssertionError("compatibility probe called a mutating entry point")
        targets = (
            "econ_theorist.runtime.layout.StoreLayout.ensure",
            "econ_theorist.runtime.replay.replay",
            "econ_theorist.runtime.recovery.recover",
            "econ_theorist.runtime.render.render_current",
            "econ_theorist.project.init_project",
            "econ_theorist.project.write_project_config",
            "econ_theorist.runtime.lock.ExclusiveFileLock.acquire",
        )
        with ExitStack() as stack:
            for target in targets:
                stack.enter_context(patch(target, side_effect=forbidden))
            result = probe_project_root(root)

        self.assertEqual(result.classification, "valid_existing")
        self.assertEqual(result.project_id, snapshot.project_id)
        self.assertEqual(result.transaction_schema, 1)
        self.assertEqual(result.chain_length, 2)
        self.assertIsNotNone(result.compatible_engine_version)
        self.assertEqual(_tree_snapshot(self.anchor), before)

    def test_frozen_phase1_chain_is_recognized_without_config_or_replay(self) -> None:
        fixture = json.loads(
            (
                REPOSITORY_ROOT
                / "tests"
                / "fixtures"
                / "phase1_frozen_v1"
                / "canonical_bytes.v1.json"
            ).read_text(encoding="utf-8")
        )["payloads"]
        genesis = base64.b64decode(fixture["genesis_transaction"])
        framing = base64.b64decode(fixture["framing_transaction"])
        genesis_digest = hashlib.sha256(genesis).hexdigest()
        framing_digest = hashlib.sha256(framing).hexdigest()
        root = self._new_root("frozen-phase1")
        transactions = root / ".econ-theorist" / "transactions" / "sha256"
        refs = root / ".econ-theorist" / "refs"
        transactions.mkdir(parents=True)
        refs.mkdir()
        (transactions / genesis_digest).write_bytes(genesis)
        (transactions / framing_digest).write_bytes(framing)
        (refs / "main").write_bytes(framing_digest.encode("ascii"))

        result = self._assert_probe_preserves(root, "valid_existing")
        self.assertEqual(result.chain_length, 2)
        self.assertEqual(result.project_id, "project.phase1.frozen.bytes")
        self.assertIn("project_config_missing", result.diagnostics)

    def test_project_config_is_only_a_diagnostic_hint(self) -> None:
        variants = ("missing", "invalid", "stale")
        for variant in variants:
            with self.subTest(variant=variant):
                root, snapshot = self._initialized(f"config-{variant}")
                config = root / ".econ-theorist" / "project.json"
                if variant == "missing":
                    config.unlink()
                elif variant == "invalid":
                    config.write_bytes(b"not-json")
                else:
                    config.write_bytes(
                        canonical_json_bytes(
                            {
                                "config_schema": 1,
                                "project_id": "project.wrong",
                                "name": "stale",
                                "scope": "economic_theory_only",
                                "engine_version": "999.0.0",
                            }
                        )
                    )
                result = self._assert_probe_preserves(root, "valid_existing")
                self.assertEqual(result.project_id, snapshot.project_id)
                if variant == "stale":
                    self.assertEqual(result.engine_version_hint, "999.0.0")
                    self.assertIn(
                        "project_config_project_id_mismatch", result.diagnostics
                    )
                else:
                    self.assertIsNone(result.engine_version_hint)

    def test_explicit_selected_project_identity_mismatch_is_corrupt(self) -> None:
        root, _ = self._initialized("identity-mismatch")
        result = self._assert_probe_preserves(
            root, "corrupt", expected_project_id="project.other"
        )
        self.assertIn("selected_project_identity_mismatch", result.diagnostics)

    def test_malformed_head_missing_target_and_digest_mismatch_are_corrupt(self) -> None:
        roots: list[Path] = []

        malformed, _ = self._initialized("bad-head")
        StoreLayout.at(malformed).main_ref.write_bytes(b"not-a-head")
        roots.append(malformed)

        missing, _ = self._initialized("missing-target")
        StoreLayout.at(missing).main_ref.write_bytes(b"d" * 64)
        roots.append(missing)

        mismatch, _ = self._initialized("digest-mismatch")
        layout = StoreLayout.at(mismatch)
        fake = "e" * 64
        (layout.transactions_root / fake).write_bytes(b"{}")
        layout.main_ref.write_bytes(fake.encode("ascii"))
        roots.append(mismatch)

        for root in roots:
            with self.subTest(root=root.name):
                self._assert_probe_preserves(root, "corrupt")

    def test_noncanonical_or_schema_inconsistent_current_transaction_is_corrupt(self) -> None:
        noncanonical, _ = self._initialized("noncanonical-transaction")
        payload, _ = self._head_payload(noncanonical)
        canonical = canonical_json_bytes(payload)
        data = canonical + b"\n"
        digest = hashlib.sha256(data).hexdigest()
        layout = StoreLayout.at(noncanonical)
        (layout.transactions_root / digest).write_bytes(data)
        layout.main_ref.write_bytes(digest.encode("ascii"))

        inconsistent, _ = self._initialized("inconsistent-transaction")
        payload, _ = self._head_payload(inconsistent)
        payload["project_id"] = "project.inconsistent"
        self._install_head_payload(inconsistent, payload)

        self._assert_probe_preserves(noncanonical, "corrupt")
        self._assert_probe_preserves(inconsistent, "corrupt")

    def test_unknown_future_transaction_schema_is_incompatible_despite_config_hint(self) -> None:
        root, _ = self._initialized("future-schema")
        payload, _ = self._head_payload(root)
        payload["transaction_schema"] = 2
        self._install_head_payload(root, payload)
        result = self._assert_probe_preserves(root, "incompatible")
        self.assertEqual(result.transaction_schema, 2)
        self.assertIn("transaction_schema_unsupported:2", result.diagnostics)

    def test_extra_ref_requires_recovery_but_invalid_config_path_is_diagnostic(self) -> None:
        extra_ref, _ = self._initialized("extra-ref")
        (StoreLayout.at(extra_ref).refs_dir / "other").write_bytes(b"f" * 64)

        config_directory, _ = self._initialized("config-directory")
        config = StoreLayout.at(config_directory).project_file
        config.unlink()
        config.mkdir()

        self._assert_probe_preserves(extra_ref, "recovery_required")
        result = self._assert_probe_preserves(config_directory, "valid_existing")
        self.assertIn("project_config_invalid", result.diagnostics)

    def test_nested_store_with_or_without_primary_store_is_corrupt(self) -> None:
        without_primary = self._new_root("nested-only")
        (without_primary / "paper" / ".econ-theorist").mkdir(parents=True)

        with_primary, _ = self._initialized("primary-and-nested")
        (with_primary / "appendix" / ".econ-theorist").mkdir(parents=True)

        self._assert_probe_preserves(without_primary, "corrupt")
        self._assert_probe_preserves(with_primary, "corrupt")

    def test_non_directory_root_or_store_is_corrupt(self) -> None:
        root_file = self.anchor / "root-file"
        root_file.write_bytes(b"not a directory")
        store_file = self._new_root("store-file")
        (store_file / ".econ-theorist").write_bytes(b"not a store")

        self._assert_probe_preserves(root_file, "corrupt")
        self._assert_probe_preserves(store_file, "corrupt")

    def test_root_and_store_symlinks_are_rejected_without_following(self) -> None:
        outside_root = self._new_root("outside-root")
        outside_store = self._new_root("outside-store")
        (outside_root / "marker").write_bytes(b"root marker")
        (outside_store / "marker").write_bytes(b"store marker")

        root_link = self.anchor / "root-link"
        store_project = self._new_root("store-link-project")
        try:
            root_link.symlink_to(outside_root, target_is_directory=True)
            (store_project / ".econ-theorist").symlink_to(
                outside_store, target_is_directory=True
            )
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlinks are unavailable: {exc}")

        self._assert_probe_preserves(root_link, "corrupt")
        self._assert_probe_preserves(store_project, "corrupt")
        self.assertEqual((outside_root / "marker").read_bytes(), b"root marker")
        self.assertEqual((outside_store / "marker").read_bytes(), b"store marker")

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_store_junction_is_rejected_without_following(self) -> None:
        root = self._new_root("junction-project")
        outside = self._new_root("junction-outside")
        marker = outside / "marker"
        marker.write_bytes(b"junction marker")
        junction = root / ".econ-theorist"
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.skipTest(f"directory junctions are unavailable: {result.stderr}")
        try:
            self._assert_probe_preserves(root, "corrupt")
            self.assertEqual(marker.read_bytes(), b"junction marker")
        finally:
            junction.rmdir()

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_selected_root_junction_is_rejected_without_following(self) -> None:
        outside = self._new_root("root-junction-outside")
        marker = outside / "marker"
        marker.write_bytes(b"root junction marker")
        junction = self.anchor / "root-junction"
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.skipTest(f"directory junctions are unavailable: {result.stderr}")
        try:
            self._assert_probe_preserves(junction, "corrupt")
            self.assertEqual(marker.read_bytes(), b"root junction marker")
        finally:
            junction.rmdir()


if __name__ == "__main__":
    unittest.main()
