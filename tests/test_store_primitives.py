"""Unit contracts for immutable storage, head writes, and the commit lock."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import assert_generated_view, sha256_bytes

from econ_theorist.runtime import (
    ExistingObjectCorrupt,
    ExclusiveFileLock,
    HeadChanged,
    HeadFormatError,
    HeadStore,
    LockTimeout,
    ObjectStore,
    StoreLayout,
    atomic_write_bytes,
)


class TemporaryStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.project_root = Path(self.temporary_directory.name)
        self.layout = StoreLayout.at(self.project_root).ensure()
        self.objects = ObjectStore(self.layout)


class ImmutableObjectStoreTests(TemporaryStoreTestCase):
    def test_install_is_content_addressed_and_idempotent(self) -> None:
        data = b"immutable transaction bytes"
        digest = sha256_bytes(data)

        first = self.objects.install_bytes("transactions", digest, data)
        second = self.objects.install_bytes("transactions", digest, data)

        self.assertEqual(self.objects.read_bytes("transactions", digest), data)
        self.assertEqual(first.path, second.path)
        self.assertEqual(first.path, self.objects.path_for("transactions", digest))
        self.assertTrue(self.objects.verify("transactions", digest))

    def test_existing_corrupt_object_is_never_overwritten(self) -> None:
        intended = b"the canonical bytes"
        digest = sha256_bytes(intended)
        target = self.objects.path_for("transactions", digest)
        target.parent.mkdir(parents=True, exist_ok=True)
        corrupt = b"pre-existing corrupt bytes"
        target.write_bytes(corrupt)

        with self.assertRaises(ExistingObjectCorrupt):
            self.objects.install_bytes("transactions", digest, intended)

        self.assertEqual(target.read_bytes(), corrupt)
        reports = list((self.layout.quarantine_dir / "reports").glob("*.json"))
        self.assertTrue(reports, "immutable conflict must leave an audit report")

    def test_atomic_write_keeps_old_value_when_replace_is_not_reached(self) -> None:
        target = self.project_root / "pointer"
        target.write_bytes(b"old")

        with patch(
            "econ_theorist.runtime.objects.inject_fault",
            side_effect=RuntimeError("injected before os.replace"),
        ):
            with self.assertRaises(RuntimeError):
                atomic_write_bytes(
                    target,
                    b"new",
                    before_replace_fault="after_temp_head_write",
                )

        self.assertEqual(target.read_bytes(), b"old")


class HeadStoreTests(TemporaryStoreTestCase):
    def test_compare_expected_head_and_leave_winner_unchanged(self) -> None:
        head = HeadStore(self.layout)
        winner = "1" * 64
        loser = "2" * 64

        head.replace(expected=None, new=winner)
        with self.assertRaises(HeadChanged):
            head.replace(expected=None, new=loser)

        self.assertEqual(head.read(), winner)
        self.assertEqual(self.layout.main_ref.read_bytes(), winner.encode("ascii"))

    def test_head_accepts_only_raw_lowercase_sha256_bytes(self) -> None:
        head = HeadStore(self.layout)
        invalid_values = (
            b"",
            b"a" * 63,
            b"A" * 64,
            b"sha256:" + b"a" * 64,
            b"a" * 64 + b"\n",
            b" a" + b"a" * 62,
            b"\xff" * 64,
        )

        for raw in invalid_values:
            with self.subTest(raw=raw):
                self.layout.main_ref.write_bytes(raw)
                with self.assertRaises(HeadFormatError):
                    head.read()

    def test_generated_view_edit_has_no_authority_over_head(self) -> None:
        head = HeadStore(self.layout)
        canonical_head = "a" * 64
        head.replace(expected=None, new=canonical_head)

        false_view = "CONFIRMED: yes\nVERIFIED: yes\nsource_head: fake\n"
        self.layout.status_view.parent.mkdir(parents=True, exist_ok=True)
        self.layout.status_view.write_text(false_view, encoding="utf-8")

        self.assertEqual(head.read(), canonical_head)
        generated = (
            "<!-- GENERATED; NONCANONICAL -->\n"
            f"source_head: {canonical_head}\n"
        )
        assert_generated_view(self, generated, canonical_head)


class ExclusiveLockTests(TemporaryStoreTestCase):
    def test_second_lock_times_out_until_first_is_released(self) -> None:
        first = ExclusiveFileLock(
            self.layout.commit_lock,
            timeout=0.25,
            poll_interval=0.01,
        )
        second = ExclusiveFileLock(
            self.layout.commit_lock,
            timeout=0.05,
            poll_interval=0.01,
        )

        first.acquire()
        self.addCleanup(first.release)
        with self.assertRaises(LockTimeout):
            second.acquire()

        first.release()
        with second:
            self.assertTrue(self.layout.commit_lock.exists())


if __name__ == "__main__":  # pragma: no cover - direct test invocation
    unittest.main()
