"""Live-write boundaries between frozen catalogs and newer typed state.

Historical v1 transactions remain replayable under their exact catalog.  A
new v1 run, however, must not create or mutate packed Phase 2 payloads, register
a blind candidate lock, or operate after Phase 2 material has entered the
project. Phase 2 likewise becomes replay-only after authoring material enters
the project, and Phase 3 becomes replay-only after profile/craft material
enters it. Those writes must use the active catalog's exact contracts.
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
from .authoring import is_packed_authoring_entity
from .profile_craft import is_packed_profile_craft_entity


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


def snapshot_has_phase3_material(snapshot: Snapshot) -> bool:
    """Whether reachable history contains a packed Phase 3 authoring payload."""

    return any(
        is_packed_authoring_entity(item) for item in snapshot.entity_versions
    )


def transaction_introduces_phase3_material(transaction: Transaction) -> bool:
    """Whether a candidate attempts a Phase 3 write under an older catalog."""

    return any(
        isinstance(operation, (CreateEntityOp, SupersedeEntityOp))
        and is_packed_authoring_entity(operation.entity)
        for operation in transaction.operations
    )


def snapshot_has_phase4_material(snapshot: Snapshot) -> bool:
    """Whether reachable history contains a packed Phase 4 payload."""

    return any(
        is_packed_profile_craft_entity(item) for item in snapshot.entity_versions
    )


def transaction_introduces_phase4_material(transaction: Transaction) -> bool:
    """Whether a candidate attempts a Phase 4 write under an older catalog."""

    return any(
        isinstance(operation, (CreateEntityOp, SupersedeEntityOp))
        and is_packed_profile_craft_entity(operation.entity)
        for operation in transaction.operations
    )


__all__ = [
    "CANDIDATE_LOCK_MEDIA_TYPE",
    "is_candidate_lock",
    "snapshot_has_phase2_material",
    "snapshot_has_phase3_material",
    "snapshot_has_phase4_material",
    "transaction_introduces_phase2_material",
    "transaction_introduces_phase3_material",
    "transaction_introduces_phase4_material",
]
