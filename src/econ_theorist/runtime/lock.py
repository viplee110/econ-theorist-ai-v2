"""Cross-platform OS file locking for serialized canonical commits."""

from __future__ import annotations

import errno
import os
import time
from pathlib import Path
from types import TracebackType

from ..errors import LockError


class LockTimeout(LockError, TimeoutError):
    """The OS lock was not acquired before the requested deadline."""

    def __init__(self, path: Path, timeout: float | None) -> None:
        self.path = path
        self.timeout = timeout
        super().__init__(f"timed out acquiring exclusive lock {path} after {timeout}s")


def _contention_error(exc: OSError) -> bool:
    return exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK} or getattr(
        exc, "winerror", None
    ) in {32, 33, 36}


def _try_os_lock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _os_unlock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(fd, fcntl.LOCK_UN)


class ExclusiveFileLock:
    """A protocol-mandatory, OS-enforced exclusive file lock.

    POSIX locks are advisory at the operating-system level; they are mandatory
    for every runtime commit path.  Windows uses a one-byte ``msvcrt`` region
    lock.  No third-party dependency or replaceable lock-directory convention
    is involved.
    """

    def __init__(
        self,
        path: str | Path,
        timeout: float | None = None,
        poll_interval: float = 0.05,
    ) -> None:
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative or None")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self.path = Path(path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._fd: int | None = None

    @property
    def acquired(self) -> bool:
        return self._fd is not None

    def acquire(self) -> "ExclusiveFileLock":
        if self._fd is not None:
            raise LockError(f"lock is already acquired: {self.path}")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            # Windows region locks require a real byte.  Creating it before the
            # lock is safe: it is permanent, carries no state, and is fsynced.
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
                os.fsync(fd)

            deadline = (
                None if self.timeout is None else time.monotonic() + self.timeout
            )
            while True:
                try:
                    _try_os_lock(fd)
                    break
                except InterruptedError:
                    continue
                except OSError as exc:
                    if not _contention_error(exc):
                        raise LockError(f"cannot lock {self.path}: {exc}") from exc
                    if deadline is not None and time.monotonic() >= deadline:
                        raise LockTimeout(self.path, self.timeout) from exc
                    delay = self.poll_interval
                    if deadline is not None:
                        delay = min(delay, max(0.0, deadline - time.monotonic()))
                    if delay:
                        time.sleep(delay)
            self._fd = fd
            return self
        except BaseException:
            os.close(fd)
            raise

    def release(self) -> None:
        fd = self._fd
        if fd is None:
            return
        self._fd = None
        try:
            _os_unlock(fd)
        except OSError as exc:
            raise LockError(f"cannot unlock {self.path}: {exc}") from exc
        finally:
            os.close(fd)

    def __enter__(self) -> "ExclusiveFileLock":
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()


def exclusive_lock(
    path: str | Path,
    timeout: float | None = None,
    poll_interval: float = 0.05,
) -> ExclusiveFileLock:
    """Return an exclusive lock suitable for use as a context manager."""

    return ExclusiveFileLock(path, timeout=timeout, poll_interval=poll_interval)
