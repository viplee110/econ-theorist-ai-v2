from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from econ_theorist.codec import canonical_json_bytes
from econ_theorist.errors import IntegrityError
from econ_theorist.machine import operational as operational_module
from econ_theorist.machine.operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    write_immutable_operational,
)


class _PartialWriteThenFail:
    """File wrapper that models a process-visible partial temp write failure."""

    def __init__(self, stream) -> None:
        self._stream = stream

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self._stream.close()
        return False

    def write(self, data: bytes) -> int:
        self._stream.write(data[: max(1, len(data) // 2)])
        self._stream.flush()
        raise OSError("injected partial temp write failure")

    def flush(self) -> None:
        self._stream.flush()

    def fileno(self) -> int:
        return self._stream.fileno()


class Phase5AOperationalAtomicPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.target = self.anchor / "operational" / "record.json"
        self.data = b'{"schema":"test/operational/v1","value":"complete"}'

    def _temporary_candidates(self) -> tuple[Path, ...]:
        if not self.target.parent.exists():
            return ()
        return tuple(self.target.parent.glob(f".{self.target.name}.tmp-*"))

    def test_partial_temp_write_failure_never_exposes_final_and_retry_succeeds(
        self,
    ) -> None:
        real_fdopen = os.fdopen

        def partially_write_then_fail(fd, *args, **kwargs):
            return _PartialWriteThenFail(real_fdopen(fd, *args, **kwargs))

        with patch.object(
            operational_module.os,
            "fdopen",
            side_effect=partially_write_then_fail,
        ):
            with self.assertRaisesRegex(OSError, "partial temp write failure"):
                write_immutable_operational(self.anchor, self.target, self.data)

        self.assertFalse(self.target.exists())
        self.assertEqual(self._temporary_candidates(), ())
        self.assertTrue(
            write_immutable_operational(self.anchor, self.target, self.data)
        )
        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertFalse(
            write_immutable_operational(self.anchor, self.target, self.data)
        )

    def test_publish_failure_cleans_complete_temp_and_exact_retry_succeeds(
        self,
    ) -> None:
        with patch.object(
            operational_module.os,
            "link",
            side_effect=OSError("injected link failure"),
        ):
            with self.assertRaisesRegex(
                OperationalError, "cannot atomically publish"
            ):
                write_immutable_operational(self.anchor, self.target, self.data)

        self.assertFalse(self.target.exists())
        self.assertEqual(self._temporary_candidates(), ())
        self.assertTrue(
            write_immutable_operational(self.anchor, self.target, self.data)
        )
        self.assertEqual(self.target.read_bytes(), self.data)

    def test_failure_after_atomic_publish_leaves_only_complete_final(self) -> None:
        real_fsync_directory = operational_module.fsync_directory

        def fail_after_publication(directory) -> None:
            if Path(directory) == self.target.parent and self.target.exists():
                raise OSError("injected post-publication durability failure")
            real_fsync_directory(directory)

        with patch.object(
            operational_module,
            "fsync_directory",
            side_effect=fail_after_publication,
        ):
            with self.assertRaisesRegex(OSError, "post-publication durability"):
                write_immutable_operational(self.anchor, self.target, self.data)

        self.assertEqual(self.target.read_bytes(), self.data)
        self.assertEqual(self._temporary_candidates(), ())
        self.assertFalse(
            write_immutable_operational(self.anchor, self.target, self.data)
        )

    def test_existing_winner_is_never_overwritten(self) -> None:
        winner = b'{"winner":"first"}'
        self.assertTrue(
            write_immutable_operational(self.anchor, self.target, winner)
        )
        with self.assertRaises(IntegrityError):
            write_immutable_operational(self.anchor, self.target, self.data)
        self.assertEqual(self.target.read_bytes(), winner)
        self.assertEqual(self._temporary_candidates(), ())

    def test_windows_extended_path_spelling_normalizes_drive_and_unc(self) -> None:
        convert = operational_module._windows_extended_path_text
        self.assertEqual(
            convert(r"C:\alpha\..\beta"),
            r"\\?\C:\beta",
        )
        self.assertEqual(
            convert(r"\\server\share\alpha"),
            r"\\?\UNC\server\share\alpha",
        )
        self.assertEqual(
            convert(r"\\?\C:\alpha\..\beta"),
            r"\\?\C:\beta",
        )
        self.assertEqual(
            convert(r"\\?\UNC\server\share\alpha"),
            r"\\?\UNC\server\share\alpha",
        )

    @unittest.skipUnless(os.name == "nt", "Windows MAX_PATH regression")
    def test_long_operational_cas_path_needs_no_user_prefix(self) -> None:
        desired_root_length = max(len(str(self.anchor)) + 2, 90)
        filler = "p" * (desired_root_length - len(str(self.anchor)) - 1)
        project_root = self.anchor / filler
        project_root.mkdir()
        run_root = (
            project_root
            / ".econ-theorist"
            / "operational"
            / "v1"
            / "runs"
            / ("run_op_" + "a" * 48)
        )
        store = ContentAddressedOperationalStore(project_root, run_root)
        value = {
            "schema": "test/long-operational/v1",
            "value": "complete",
        }
        expected = canonical_json_bytes(value)

        digest, target = store.install(
            "framing-team-delivery-authorizations", value
        )
        self.addCleanup(
            operational_module._operational_io_path(target).unlink,
            missing_ok=True,
        )
        self.assertGreater(len(str(target)), 260)
        self.assertFalse(str(target).startswith("\\\\?\\"))
        self.assertEqual(
            store.read_bytes(
                "framing-team-delivery-authorizations", digest
            ),
            expected,
        )

        repeated_digest, repeated_target = store.install(
            "framing-team-delivery-authorizations", value
        )
        self.assertEqual((repeated_digest, repeated_target), (digest, target))
        with self.assertRaises(IntegrityError):
            write_immutable_operational(
                project_root, target, b'{"different":true}'
            )


if __name__ == "__main__":
    unittest.main()
