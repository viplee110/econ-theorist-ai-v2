"""Fail-closed filesystem and projection-boundary regression tests."""

from __future__ import annotations

import importlib
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.helpers import assert_generated_view, sha256_bytes

from econ_theorist.codec import transaction_bytes, transaction_digest
from econ_theorist.models import (
    Actor,
    CreateEntityOp,
    EntityVersion,
    FacetPayloads,
    ScientificStatus,
    Transaction,
)
from econ_theorist.runtime import (
    ExclusiveFileLock,
    HeadChanged,
    HeadStore,
    LockTimeout,
    ObjectStore,
    StoreLayout,
)
from econ_theorist.runtime.layout import UnsafeStorePath, _is_reparse
from econ_theorist.runtime.recovery import recover
from econ_theorist.runtime.render import render_current, write_status_view


class StoreBoundaryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.layout = StoreLayout.at(self.root / "project").ensure()

    def make_directory_link(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target, target_is_directory=True)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"directory symlinks are unavailable: {exc}")

    def make_file_link(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"file symlinks are unavailable: {exc}")

    def make_directory_junction(self, link: Path, target: Path) -> None:
        if os.name != "nt":
            self.skipTest("Windows junction test")
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self.skipTest(f"directory junctions are unavailable: {result.stderr}")


class LayoutBoundaryTests(StoreBoundaryTestCase):
    def test_windows_reparse_attribute_is_recognized(self) -> None:
        metadata = SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=getattr(
                stat,
                "FILE_ATTRIBUTE_REPARSE_POINT",
                0x400,
            ),
        )
        self.assertTrue(_is_reparse(metadata))

    def test_store_root_symlink_is_rejected(self) -> None:
        project = self.root / "linked-project"
        outside = self.root / "outside-store"
        project.mkdir()
        outside.mkdir()
        self.make_directory_link(project / ".econ-theorist", outside)

        with self.assertRaises(UnsafeStorePath):
            StoreLayout.at(project).ensure()

    def test_store_root_windows_junction_is_rejected(self) -> None:
        project = self.root / "junction-project"
        outside = self.root / "outside-junction"
        project.mkdir()
        outside.mkdir()
        link = project / ".econ-theorist"
        self.make_directory_junction(link, outside)
        try:
            with self.assertRaises(UnsafeStorePath):
                StoreLayout.at(project).ensure()
        finally:
            # rmdir removes the junction entry, never its target tree.
            link.rmdir()

    def test_nested_required_directory_symlink_is_rejected(self) -> None:
        project = self.root / "nested-link-project"
        store = project / ".econ-theorist"
        outside = self.root / "outside-runs"
        store.mkdir(parents=True)
        outside.mkdir()
        self.make_directory_link(store / "runs", outside)

        with self.assertRaises(UnsafeStorePath):
            StoreLayout.at(project).ensure()

    def test_non_directory_at_required_path_is_rejected(self) -> None:
        project = self.root / "wrong-kind-project"
        runs = project / ".econ-theorist" / "runs"
        runs.parent.mkdir(parents=True)
        runs.write_bytes(b"not a runtime directory")

        with self.assertRaises(UnsafeStorePath):
            StoreLayout.at(project).ensure()


class HeadAndObjectBoundaryTests(StoreBoundaryTestCase):
    def test_head_symlink_is_not_followed(self) -> None:
        target = self.root / "outside-head"
        target.write_bytes(b"a" * 64)
        self.make_file_link(self.layout.main_ref, target)

        with self.assertRaises(UnsafeStorePath):
            HeadStore(self.layout).read()

    def test_head_directory_is_rejected(self) -> None:
        self.layout.main_ref.mkdir()
        with self.assertRaises(UnsafeStorePath):
            HeadStore(self.layout).read()

    def test_object_symlink_is_not_read_or_treated_as_idempotent(self) -> None:
        data = b"canonical-looking bytes"
        digest = sha256_bytes(data)
        target = ObjectStore(self.layout).path_for("transactions", digest)
        outside = self.root / "outside-object"
        outside.write_bytes(data)
        self.make_file_link(target, outside)

        objects = ObjectStore(self.layout)
        with self.assertRaises(UnsafeStorePath):
            objects.read_bytes("transactions", digest)
        with self.assertRaises(UnsafeStorePath):
            objects.install_bytes("transactions", digest, data)

    def test_nonregular_object_target_is_rejected(self) -> None:
        data = b"not a directory"
        digest = sha256_bytes(data)
        objects = ObjectStore(self.layout)
        target = objects.path_for("transactions", digest)
        target.mkdir()

        with self.assertRaises(UnsafeStorePath):
            objects.read_bytes("transactions", digest)
        with self.assertRaises(UnsafeStorePath):
            objects.install_bytes("transactions", digest, data)

    def test_namespace_symlink_cannot_redirect_installation(self) -> None:
        outside = self.root / "outside-namespace"
        outside.mkdir()
        self.make_directory_link(self.layout.store_root / "malicious", outside)

        with self.assertRaises(UnsafeStorePath):
            ObjectStore(self.layout).install_bytes("malicious", None, b"payload")
        self.assertEqual(tuple(outside.iterdir()), ())

    def test_non_directory_namespace_cannot_receive_installation(self) -> None:
        namespace = self.layout.store_root / "malicious"
        namespace.write_bytes(b"not a namespace directory")

        with self.assertRaises(UnsafeStorePath):
            ObjectStore(self.layout).install_bytes("malicious", None, b"payload")


class RenderAndRecoveryBoundaryTests(StoreBoundaryTestCase):
    @staticmethod
    def empty_snapshot(head: str) -> SimpleNamespace:
        return SimpleNamespace(
            head=head,
            project_id="prj_boundary",
            chain=(),
            entity_versions=(),
            current_entities={},
            derived_status={},
            decisions=(),
            effective_decisions={},
            artifacts=(),
            current_artifacts={},
            blockers=(),
        )

    def test_stale_snapshot_cannot_overwrite_newer_view(self) -> None:
        current = "a" * 64
        stale = "b" * 64
        HeadStore(self.layout).replace(None, current)
        sentinel = "newer generated view\n"
        self.layout.status_view.write_text(sentinel, encoding="utf-8")

        with self.assertRaises(HeadChanged):
            write_status_view(self.layout, self.empty_snapshot(stale))

        self.assertEqual(self.layout.status_view.read_text(encoding="utf-8"), sentinel)

    def test_render_current_holds_commit_lock_through_write(self) -> None:
        head = "c" * 64
        HeadStore(self.layout).replace(None, head)
        snapshot = self.empty_snapshot(head)
        replay_module = importlib.import_module("econ_theorist.runtime.replay")

        def replay_while_probing_lock(_layout: StoreLayout) -> SimpleNamespace:
            with self.assertRaises(LockTimeout):
                with ExclusiveFileLock(
                    self.layout.commit_lock,
                    timeout=0.03,
                    poll_interval=0.005,
                ):
                    pass
            return snapshot

        with patch.object(
            replay_module,
            "replay",
            side_effect=replay_while_probing_lock,
        ):
            result = render_current(self.layout)

        self.assertEqual(result.source_head, head)
        self.assertEqual(result.path, self.layout.status_view)
        assert_generated_view(
            self,
            self.layout.status_view.read_text(encoding="utf-8"),
            head,
        )

    def test_recovery_reports_unreachable_provenance(self) -> None:
        data = b"unreachable route provenance"
        digest = sha256_bytes(data)
        ObjectStore(self.layout).install_bytes("provenance", digest, data)

        report = recover(self.layout)

        self.assertIsNone(report.head)
        self.assertIn(digest, report.orphans.provenance_digests)

    def test_recovery_reports_but_never_promotes_pre_head_genesis(self) -> None:
        project_id = "project.pre_head"
        project = EntityVersion(
            entity_id=project_id,
            entity_type="Project",
            version=1,
            project_id=project_id,
            title="Interrupted initialization",
            summary="A valid genesis whose head publication did not occur.",
            status=ScientificStatus(lifecycle="active"),
            facets=FacetPayloads(),
            created_at="2026-07-11T00:00:00Z",
        )
        transaction = Transaction(
            transaction_id="txn.pre_head_genesis",
            origin="genesis",
            project_id=project_id,
            base_revision=None,
            route_run_id="run.pre_head_genesis",
            actor=Actor(kind="human", actor_id="human.test"),
            intent="Initialize one interrupted theory project",
            operations=(CreateEntityOp(entity=project),),
            created_at="2026-07-11T00:00:00Z",
            parent_transaction_hash=None,
        )
        digest = transaction_digest(transaction)
        ObjectStore(self.layout).install_bytes(
            "transactions",
            digest,
            transaction_bytes(transaction),
        )

        report = recover(self.layout)

        self.assertEqual(report.recovery_state, "pre_head_genesis_candidate")
        self.assertEqual(
            tuple(
                candidate.transaction_digest
                for candidate in report.genesis_resume_candidates
            ),
            (digest,),
        )
        self.assertIn("Do not edit refs/main", report.recommended_action or "")
        self.assertIsNone(HeadStore(self.layout).read())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
