"""Persist explicit human/agent Decision records as immutable transactions."""

from __future__ import annotations

from pathlib import Path

from .ids import new_id, utc_now
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


def commit_decision(layout: StoreLayout, decision: Decision) -> CommitResult:
    """Commit one Decision at the current head.

    Phase 1 treats ``Actor(kind='human')`` as an explicit local provenance
    assertion, not cryptographic authentication. The immutable record still
    carries the complete choice, alternatives, evidence, dissent, and risks.
    """

    snapshot = replay(layout)
    if decision.project_id != snapshot.project_id:
        raise DecisionInputError("Decision belongs to a different project")
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
        transaction_id=new_id("txn_decision"),
        origin="human_decision",
        project_id=snapshot.project_id,
        base_revision=snapshot.head,
        route_run_id=new_id("run_decision"),
        actor=decision.decider,
        intent=f"Record {decision.decision_kind} Decision {decision.decision_id}@{decision.version}.",
        operations=(operation,),
        privacy=decision.privacy,
        access_compartments=decision.access_compartments,
        created_at=utc_now(),
        parent_transaction_hash=snapshot.head,
    )
    return commit_transaction(layout, transaction)
