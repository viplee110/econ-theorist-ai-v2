from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist import runs as runs_module
from econ_theorist import staging as staging_module
from econ_theorist.runs import ImmutableRunConflict, RunError
from econ_theorist.staging import StagingError


class _PartialWriteThenFail:
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


class RunAndStagingAtomicPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.data = b'{"schema":"test/immutable/v1","value":"complete"}'

    def _publishers(self):
        return (
            (
                "run",
                runs_module,
                lambda path, data: runs_module._write_new(
                    path, data, immutable=True
                ),
                (RunError, ImmutableRunConflict),
            ),
            (
                "staging",
                staging_module,
                staging_module._write_immutable,
                (StagingError,),
            ),
        )

    @staticmethod
    def _temporary_candidates(target: Path) -> tuple[Path, ...]:
        if not target.parent.exists():
            return ()
        return tuple(target.parent.glob(f".{target.name}.tmp-*"))

    def test_partial_temp_write_failure_never_exposes_final(self) -> None:
        for name, module, publish, _ in self._publishers():
            with self.subTest(publisher=name):
                target = self.root / name / "partial" / "record.json"
                real_fdopen = os.fdopen

                def partially_write_then_fail(fd, *args, **kwargs):
                    return _PartialWriteThenFail(real_fdopen(fd, *args, **kwargs))

                with patch.object(
                    module.os,
                    "fdopen",
                    side_effect=partially_write_then_fail,
                ):
                    with self.assertRaisesRegex(
                        OSError, "partial temp write failure"
                    ):
                        publish(target, self.data)

                self.assertFalse(target.exists())
                self.assertEqual(self._temporary_candidates(target), ())
                publish(target, self.data)
                self.assertEqual(target.read_bytes(), self.data)

    def test_publish_failure_cleans_temp_and_retry_succeeds(self) -> None:
        for name, module, publish, error_types in self._publishers():
            with self.subTest(publisher=name):
                target = self.root / name / "link-failure" / "record.json"
                with patch.object(
                    module.os,
                    "link",
                    side_effect=OSError("injected link failure"),
                ):
                    with self.assertRaises(error_types):
                        publish(target, self.data)

                self.assertFalse(target.exists())
                self.assertEqual(self._temporary_candidates(target), ())
                publish(target, self.data)
                self.assertEqual(target.read_bytes(), self.data)

    def test_post_publish_fsync_failure_leaves_complete_final(self) -> None:
        for name, module, publish, error_types in self._publishers():
            with self.subTest(publisher=name):
                target = self.root / name / "fsync-failure" / "record.json"
                real_fsync_directory = module.fsync_directory

                def fail_after_publication(directory) -> None:
                    if Path(directory) == target.parent and target.exists():
                        raise OSError("injected post-publication fsync failure")
                    real_fsync_directory(directory)

                with patch.object(
                    module,
                    "fsync_directory",
                    side_effect=fail_after_publication,
                ):
                    with self.assertRaises(error_types):
                        publish(target, self.data)

                self.assertEqual(target.read_bytes(), self.data)
                self.assertEqual(self._temporary_candidates(target), ())
                publish(target, self.data)
                self.assertEqual(target.read_bytes(), self.data)

    def test_concurrent_competing_publications_never_mix_or_overwrite(self) -> None:
        contenders = tuple(
            f'{{"publisher":{index},"padding":"{index * "x"}"}}'.encode()
            for index in range(1, 13)
        )
        for name, _, publish, error_types in self._publishers():
            with self.subTest(publisher=name):
                target = self.root / name / "concurrent" / "record.json"
                barrier = threading.Barrier(len(contenders))

                def attempt(data: bytes):
                    barrier.wait()
                    try:
                        publish(target, data)
                    except BaseException as exc:
                        return exc
                    return None

                with ThreadPoolExecutor(max_workers=len(contenders)) as executor:
                    outcomes = tuple(executor.map(attempt, contenders))

                winner = target.read_bytes()
                self.assertIn(winner, contenders)
                self.assertTrue(any(outcome is None for outcome in outcomes))
                failures = tuple(
                    outcome for outcome in outcomes if outcome is not None
                )
                self.assertTrue(failures)
                self.assertTrue(
                    all(isinstance(outcome, error_types) for outcome in failures)
                )
                self.assertEqual(self._temporary_candidates(target), ())

                with self.assertRaises(error_types):
                    publish(target, b'{"different":"cannot replace winner"}')
                self.assertEqual(target.read_bytes(), winner)

    def test_stale_temp_is_ignored_and_never_published(self) -> None:
        for name, _, publish, _ in self._publishers():
            with self.subTest(publisher=name):
                target = self.root / name / "stale-temp" / "record.json"
                target.parent.mkdir(parents=True)
                stale = target.parent / f".{target.name}.tmp-stale-crash"
                stale.write_bytes(b"partial-crash-residue")

                publish(target, self.data)

                self.assertEqual(target.read_bytes(), self.data)
                self.assertEqual(stale.read_bytes(), b"partial-crash-residue")
                self.assertEqual(self._temporary_candidates(target), (stale,))


if __name__ == "__main__":
    unittest.main()
