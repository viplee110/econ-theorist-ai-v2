"""Persist explicit human/agent Decision records as immutable transactions."""

from __future__ import annotations

from pathlib import Path

from .ids import new_id, utc_now
from .framing_quality_validation import (
    FramingQualityValidationError,
    validate_current_g1_framing_decision,
)
from .models import (
    Decision,
    RecordDecisionOp,
    SupersedeDecisionOp,
    Transaction,
)
from .runtime import StoreLayout
from .runtime.commit import CommitResult, commit_transaction
from .runtime.replay import replay


class DecisionInputError(ValueError):
    """A supplied Decision file cannot be bound to the current project."""


def read_decision(path: str | Path) -> Decision:
    try:
        return Decision.model_validate_json(Path(path).read_bytes(), strict=True)
    except (OSError, ValueError) as exc:
        raise DecisionInputError(f"Decision file is unavailable or invalid: {path}") from exc


def commit_decision(
    layout: StoreLayout,
    decision: Decision,
    *,
    expected_head: str | None = None,
    transaction_id: str | None = None,
    route_run_id: str | None = None,
    created_at: str | None = None,
) -> CommitResult:
    """Commit one Decision at the current head.

    Phase 1 treats ``Actor(kind='human')`` as an explicit local provenance
    assertion, not cryptographic authentication. The immutable record still
    carries the complete choice, alternatives, evidence, dissent, and risks.
    """

    snapshot = replay(layout)
    if expected_head is not None and snapshot.head != expected_head:
        raise DecisionInputError(
            f"Decision approval head {expected_head} differs from current head {snapshot.head}"
        )
    if decision.project_id != snapshot.project_id:
        raise DecisionInputError("Decision belongs to a different project")
    try:
        validate_current_g1_framing_decision(snapshot, decision)
    except FramingQualityValidationError as exc:
        raise DecisionInputError(f"G1 framing preflight rejected the Decision: {exc}") from exc
    if decision.version == 1:
        operation = RecordDecisionOp(decision=decision)
    else:
        if decision.supersedes is None:
            raise DecisionInputError("Decision supersession requires an exact predecessor")
        operation = SupersedeDecisionOp(
            previous=decision.supersedes,
            decision=decision,
        )
    transaction = Transaction(
        transaction_id=transaction_id or new_id("txn_decision"),
        origin="human_decision",
        project_id=snapshot.project_id,
        base_revision=snapshot.head,
        route_run_id=route_run_id or new_id("run_decision"),
        actor=decision.decider,
        intent=f"Record {decision.decision_kind} Decision {decision.decision_id}@{decision.version}.",
        operations=(operation,),
        privacy=decision.privacy,
        access_compartments=decision.access_compartments,
        created_at=created_at or utc_now(),
        parent_transaction_hash=snapshot.head,
    )
    return commit_transaction(layout, transaction)
