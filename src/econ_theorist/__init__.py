"""Theory-only walking substrate for econ-theorist-ai v2."""

from .codec import (
    canonical_json_bytes,
    object_digest,
    sha256_digest,
    transaction_bytes,
    transaction_digest,
)
from .errors import EconTheoristError
from .models import Transaction

__all__ = [
    "EconTheoristError",
    "Transaction",
    "canonical_json_bytes",
    "object_digest",
    "sha256_digest",
    "transaction_bytes",
    "transaction_digest",
]
__version__ = "0.1.0"
