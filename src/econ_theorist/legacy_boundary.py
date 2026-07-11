"""Live-write boundary between the frozen v1 substrate and Phase 2 state.

Historical v1 transactions remain replayable under their exact catalog.  A
new v1 run, however, must not create or mutate packed Phase 2 payloads, register
a blind candidate lock, or operate after Phase 2 material has entered the
project.  Those writes must use the active v2 scientific contracts.
"""

from __future__ import annotations

from .models import (
    ArtifactRegistration,
    CreateEntityOp,
    RegisterArtifactOp,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from .theory import is_packed_theory_entity


CANDIDATE_LOCK_MEDIA_TYPE = (
    "application/vnd.econ-theorist.candidate-lock+json"
)


def is_candidate_lock(artifact: ArtifactRegistration) -> bool:
    """Recognize a blind lock even when only its ID or media type is honest."""

    return artifact.artifact_id.startswith("candidate.lock.") or (
        artifact.media_type == CANDIDATE_LOCK_MEDIA_TYPE
    )


def snapshot_has_phase2_material(snapshot: Snapshot) -> bool:
    """Whether any reachable history has crossed into the Phase 2 contract."""

    return any(is_packed_theory_entity(item) for item in snapshot.entity_versions) or any(
        is_candidate_lock(item) for item in snapshot.artifacts
    )


def transaction_introduces_phase2_material(transaction: Transaction) -> bool:
    """Whether a candidate attempts a Phase 2 write under another catalog."""

    for operation in transaction.operations:
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            if is_packed_theory_entity(operation.entity):
                return True
        elif isinstance(operation, RegisterArtifactOp):
            if is_candidate_lock(operation.artifact):
                return True
    return False


__all__ = [
    "CANDIDATE_LOCK_MEDIA_TYPE",
    "is_candidate_lock",
    "snapshot_has_phase2_material",
    "transaction_introduces_phase2_material",
]
