"""Exception hierarchy for the local walking substrate."""

from __future__ import annotations


class EconTheoristError(Exception):
    """Base class for expected runtime failures."""


class CanonicalEncodingError(EconTheoristError, ValueError):
    """Raised when a value cannot enter the canonical JSON boundary."""


class RuntimeStoreError(EconTheoristError):
    """Base class for local canonical-store failures."""


class IntegrityError(RuntimeStoreError):
    """Raised when immutable content fails an integrity invariant."""


class HashMismatchError(IntegrityError):
    """Raised when bytes do not match their declared SHA-256 digest."""


class DigestCollisionError(IntegrityError):
    """Raised when an occupied digest path contains different bytes."""


class LockError(RuntimeStoreError):
    """Raised when the mandatory exclusive commit lock cannot be used."""


class PolicyError(EconTheoristError, ValueError):
    """Raised when an authority or route policy is violated."""


class AuthorityError(PolicyError):
    """Raised when an actor or Decision lacks required authority."""


class RegistryError(PolicyError):
    """Raised when a versioned policy registry is invalid or incomplete."""
