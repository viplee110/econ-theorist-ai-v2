"""Trusted-human challenge, receipt, ledger, and Decision consumption."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from pathlib import Path

from ..codec import canonical_json_bytes, sha256_digest
from ..decisions import DecisionInputError, commit_decision
from ..ids import new_id, utc_now
from ..models import Decision
from ..runtime.layout import (
    StoreLayout,
    assert_safe_store_path,
    path_entry_exists,
)
from ..runtime.lock import ExclusiveFileLock
from ..runtime.replay import replay
from .models import (
    DecisionConfirmationResultV1,
    HumanApprovalChallengeV1,
    HumanApprovalReceiptV1,
    LedgerEventV1,
)
from .operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
    write_immutable_operational,
)


class ApprovalError(OperationalError):
    """A human approval is missing, invalid, stale, expired, or already used."""


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalError(f"invalid approval timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ApprovalError("approval timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _receipt_payload(receipt: HumanApprovalReceiptV1) -> dict[str, object]:
    return receipt.model_dump(mode="json", exclude={"authenticator"})


def _authenticator(secret: bytes, payload: dict[str, object]) -> str:
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ApprovalError("trusted-channel secret must contain at least 32 bytes")
    return hmac.new(secret, canonical_json_bytes(payload), hashlib.sha256).hexdigest()


def create_human_approval_challenge(
    decision: Decision,
    *,
    head: str,
    action: str = "decision.confirm",
    blast_radius_summary: str,
    expires_at: str,
    challenge_id: str | None = None,
) -> HumanApprovalChallengeV1:
    if decision.required_authority not in {"L2", "L3"}:
        raise ApprovalError("trusted approval receipts are only for L2/L3 actions")
    if decision.selected_option is None:
        raise ApprovalError("approval challenge requires one selected option")
    return HumanApprovalChallengeV1(
        challenge_id=challenge_id or new_id("approval_challenge"),
        project_id=decision.project_id,
        head=head,
        action=action,
        decision_digest=sha256_digest(canonical_json_bytes(decision)),
        options=decision.options,
        selected_option=decision.selected_option,
        authority_level=decision.required_authority,
        blast_radius_summary=blast_radius_summary,
        expires_at=expires_at,
    )


class HmacTrustedHumanChannel:
    """Reference trusted-channel adapter used by tests and host integrations.

    It is intentionally not part of the model-callable machine dispatcher.
    Real host adapters must keep both the direct-user gesture and this secret
    outside the model's filesystem/tool scope.
    """

    def __init__(self, channel_id: str, secret: bytes) -> None:
        if not channel_id:
            raise ApprovalError("trusted channel ID must be non-empty")
        if len(secret) < 32:
            raise ApprovalError("trusted channel secret must contain at least 32 bytes")
        self.channel_id = channel_id
        self._secret = secret

    def issue(
        self,
        challenge: HumanApprovalChallengeV1,
        *,
        direct_user_gesture: bool,
        issued_at: str | None = None,
        nonce: str | None = None,
    ) -> HumanApprovalReceiptV1:
        if not direct_user_gesture:
            raise ApprovalError("a model assertion is not a direct trusted-user gesture")
        issued = issued_at or utc_now()
        if _parse_time(issued) >= _parse_time(challenge.expires_at):
            raise ApprovalError("approval challenge is already expired")
        token = nonce or secrets.token_hex(24)
        challenge_hash = sha256_digest(canonical_json_bytes(challenge))
        receipt_id = "approval_" + sha256_digest(
            canonical_json_bytes(
                {
                    "challenge_hash": challenge_hash,
                    "issuer_channel_id": self.channel_id,
                    "nonce": token,
                }
            )
        )[:48]
        unsigned: dict[str, object] = {
            "receipt_schema": "econ-theorist/human-approval-receipt/v1",
            "receipt_id": receipt_id,
            "challenge_hash": challenge_hash,
            "project_id": challenge.project_id,
            "head": challenge.head,
            "action": challenge.action,
            "decision_digest": challenge.decision_digest,
            "selected_option": challenge.selected_option,
            "authority_level": challenge.authority_level,
            "issued_at": issued,
            "expires_at": challenge.expires_at,
            "issuer_channel_id": self.channel_id,
            "nonce": token,
        }
        return HumanApprovalReceiptV1(
            **unsigned,
            authenticator=_authenticator(self._secret, unsigned),
        )

    def verify(self, receipt: HumanApprovalReceiptV1) -> None:
        if receipt.issuer_channel_id != self.channel_id:
            raise ApprovalError("approval receipt names a different trusted channel")
        expected = _authenticator(self._secret, _receipt_payload(receipt))
        if not hmac.compare_digest(expected, receipt.authenticator):
            raise ApprovalError("approval receipt authenticator is invalid")


def _subject_root(
    operational: ProjectOperationalLayout, receipt_id: str
) -> Path:
    if not receipt_id.startswith("approval_") or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789_"
        for character in receipt_id
    ):
        raise ApprovalError("unsafe approval receipt ID")
    return operational.approvals / receipt_id


def _events(
    operational: ProjectOperationalLayout, receipt_id: str
) -> tuple[tuple[str, LedgerEventV1], ...]:
    root = _subject_root(operational, receipt_id) / "events"
    if not path_entry_exists(root):
        return ()
    assert_safe_store_path(
        operational.project_root,
        root,
        expected="directory",
        allow_missing=False,
    )
    result: list[tuple[str, LedgerEventV1]] = []
    previous: str | None = None
    for sequence, path in enumerate(sorted(root.glob("*.json")), start=1):
        try:
            assert_safe_store_path(
                operational.project_root,
                path,
                expected="file",
                allow_missing=False,
            )
            data = path.read_bytes()
            event = LedgerEventV1.model_validate_json(data, strict=True)
        except (OSError, ValueError) as exc:
            raise ApprovalError("approval ledger event is invalid") from exc
        digest = sha256_digest(data)
        if (
            canonical_json_bytes(event) != data
            or event.ledger_kind != "approval"
            or event.subject_id != receipt_id
            or event.sequence != sequence
            or event.previous_event_hash != previous
            or path.name != f"{sequence:08d}-{digest}.json"
        ):
            raise ApprovalError("approval ledger chain is inconsistent")
        result.append((digest, event))
        previous = digest
    return tuple(result)


def _append_event(
    operational: ProjectOperationalLayout,
    receipt_id: str,
    *,
    event: str,
    operation_key: str | None,
    request_digest: str | None,
    payload_hash: str | None,
    recorded_at: str | None = None,
) -> LedgerEventV1:
    existing = _events(operational, receipt_id)
    record = LedgerEventV1(
        ledger_kind="approval",
        subject_id=receipt_id,
        sequence=len(existing) + 1,
        event=event,
        operation_key=operation_key,
        request_digest=request_digest,
        payload_hash=payload_hash,
        previous_event_hash=existing[-1][0] if existing else None,
        recorded_at=recorded_at or utc_now(),
    )
    data = canonical_json_bytes(record)
    digest = sha256_digest(data)
    path = (
        _subject_root(operational, receipt_id)
        / "events"
        / f"{record.sequence:08d}-{digest}.json"
    )
    write_immutable_operational(operational.project_root, path, data)
    return record


def record_approval_issued(
    operational: ProjectOperationalLayout,
    challenge: HumanApprovalChallengeV1,
    receipt: HumanApprovalReceiptV1,
    channel: HmacTrustedHumanChannel,
) -> str:
    operational.ensure()
    channel.verify(receipt)
    challenge_hash = sha256_digest(canonical_json_bytes(challenge))
    if (
        receipt.challenge_hash != challenge_hash
        or receipt.project_id != challenge.project_id
        or receipt.head != challenge.head
        or receipt.action != challenge.action
        or receipt.decision_digest != challenge.decision_digest
        or receipt.selected_option != challenge.selected_option
        or receipt.authority_level != challenge.authority_level
        or receipt.expires_at != challenge.expires_at
    ):
        raise ApprovalError("approval receipt differs from its exact challenge")
    root = _subject_root(operational, receipt.receipt_id)
    store = ContentAddressedOperationalStore(operational.project_root, root)
    challenge_digest, _ = store.install("challenges", challenge)
    receipt_digest, _ = store.install("receipts", receipt)
    with ExclusiveFileLock(operational.approval_lock):
        existing = _events(operational, receipt.receipt_id)
        if existing:
            if (
                existing[0][1].event != "issued"
                or existing[0][1].payload_hash != receipt_digest
            ):
                raise ApprovalError("approval receipt ID is already bound differently")
            return receipt_digest
        _append_event(
            operational,
            receipt.receipt_id,
            event="issued",
            operation_key=None,
            request_digest=challenge_digest,
            payload_hash=receipt_digest,
            recorded_at=receipt.issued_at,
        )
    return receipt_digest


def revoke_approval(
    operational: ProjectOperationalLayout,
    receipt_id: str,
    *,
    trusted_channel: bool,
) -> None:
    if not trusted_channel:
        raise ApprovalError("approval revocation requires the trusted-human channel")
    operational.ensure()
    with ExclusiveFileLock(operational.approval_lock):
        existing = _events(operational, receipt_id)
        if not existing or existing[-1][1].event in {
            "consumed",
            "revoked",
            "expired",
            "terminal_failure",
        }:
            raise ApprovalError("approval cannot be revoked in its current state")
        _append_event(
            operational,
            receipt_id,
            event="revoked",
            operation_key=None,
            request_digest=None,
            payload_hash=None,
        )


def _validate_for_reservation(
    operational: ProjectOperationalLayout,
    challenge: HumanApprovalChallengeV1,
    receipt: HumanApprovalReceiptV1,
    channel: HmacTrustedHumanChannel,
    *,
    operation_key: str,
    request_digest: str,
    now: str,
) -> tuple[tuple[str, LedgerEventV1], ...]:
    channel.verify(receipt)
    if receipt.challenge_hash != sha256_digest(canonical_json_bytes(challenge)):
        raise ApprovalError("receipt does not bind the supplied challenge")
    if _parse_time(now) >= _parse_time(receipt.expires_at):
        existing = _events(operational, receipt.receipt_id)
        if existing and existing[-1][1].event not in {
            "consumed",
            "revoked",
            "expired",
            "terminal_failure",
        }:
            _append_event(
                operational,
                receipt.receipt_id,
                event="expired",
                operation_key=None,
                request_digest=None,
                payload_hash=None,
                recorded_at=now,
            )
        raise ApprovalError("approval receipt is expired")
    existing = _events(operational, receipt.receipt_id)
    if not existing or existing[0][1].event != "issued":
        raise ApprovalError("approval receipt was not issued through the trusted ledger")
    terminal = existing[-1][1]
    if terminal.event == "reserved":
        if terminal.operation_key != operation_key or terminal.request_digest != request_digest:
            raise ApprovalError("approval receipt is reserved by another operation")
        return existing
    if terminal.event in {"consumed", "terminal_failure"}:
        if (
            terminal.operation_key == operation_key
            and terminal.request_digest == request_digest
        ):
            return existing
        raise ApprovalError(f"approval receipt is terminal: {terminal.event}")
    if terminal.event != "issued":
        raise ApprovalError(f"approval receipt is terminal: {terminal.event}")
    _append_event(
        operational,
        receipt.receipt_id,
        event="reserved",
        operation_key=operation_key,
        request_digest=request_digest,
        payload_hash=receipt.decision_digest,
        recorded_at=now,
    )
    return _events(operational, receipt.receipt_id)


def confirm_decision_with_receipt(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    *,
    operation_key: str,
    request_digest: str,
    decision: Decision,
    challenge: HumanApprovalChallengeV1,
    receipt: HumanApprovalReceiptV1,
    channel: HmacTrustedHumanChannel,
    now: str | None = None,
) -> DecisionConfirmationResultV1:
    """Consume one exact approval at the canonical commit boundary."""

    timestamp = now or utc_now()
    decision_digest = sha256_digest(canonical_json_bytes(decision))
    if (
        challenge.action != "decision.confirm"
        or challenge.decision_digest != decision_digest
        or challenge.project_id != decision.project_id
        or challenge.options != decision.options
        or challenge.selected_option != decision.selected_option
        or challenge.authority_level != decision.required_authority
        or receipt.decision_digest != decision_digest
    ):
        raise ApprovalError("Decision bytes/options differ from the approval challenge")
    operational.ensure()
    with ExclusiveFileLock(operational.approval_lock):
        approval_events = _validate_for_reservation(
            operational,
            challenge,
            receipt,
            channel,
            operation_key=operation_key,
            request_digest=request_digest,
            now=timestamp,
        )
        snapshot = replay(layout)
        existing = any(item == decision for item in snapshot.decisions)
        terminal_event = approval_events[-1][1].event
        if existing:
            if terminal_event == "terminal_failure":
                raise ApprovalError(
                    "terminal-failure approval unexpectedly has a canonical effect"
                )
            if terminal_event != "consumed":
                _append_event(
                    operational,
                    receipt.receipt_id,
                    event="consumed",
                    operation_key=operation_key,
                    request_digest=request_digest,
                    payload_hash=decision_digest,
                    recorded_at=timestamp,
                )
            return DecisionConfirmationResultV1(
                status="already_committed",
                decision_digest=decision_digest,
                transaction_digest=None,
                head_before=challenge.head,
                head_after=snapshot.head,
            )
        if terminal_event == "consumed":
            raise ApprovalError(
                "consumed approval has no matching canonical Decision"
            )
        if terminal_event == "terminal_failure":
            return DecisionConfirmationResultV1(
                status="stale_base",
                decision_digest=decision_digest,
                transaction_digest=None,
                head_before=challenge.head,
                head_after=snapshot.head,
            )
        if snapshot.head != challenge.head or receipt.head != challenge.head:
            _append_event(
                operational,
                receipt.receipt_id,
                event="terminal_failure",
                operation_key=operation_key,
                request_digest=request_digest,
                payload_hash=snapshot.head,
                recorded_at=timestamp,
            )
            return DecisionConfirmationResultV1(
                status="stale_base",
                decision_digest=decision_digest,
                transaction_digest=None,
                head_before=challenge.head,
                head_after=snapshot.head,
            )
        seed = sha256_digest(
            canonical_json_bytes(
                {
                    "operation_key": operation_key,
                    "receipt_id": receipt.receipt_id,
                    "decision_digest": decision_digest,
                }
            )
        )
        try:
            result = commit_decision(
                layout,
                decision,
                expected_head=challenge.head,
                transaction_id=f"txn_decision_{seed[:48]}",
                route_run_id=f"run_decision_{seed[:48]}",
                created_at=receipt.issued_at,
            )
        except DecisionInputError as exc:
            _append_event(
                operational,
                receipt.receipt_id,
                event="terminal_failure",
                operation_key=operation_key,
                request_digest=request_digest,
                payload_hash=decision_digest,
                recorded_at=timestamp,
            )
            raise ApprovalError(
                f"canonical Decision preflight rejected the approval: {exc}"
            ) from exc
        if result.status != "committed" or result.head_after is None:
            _append_event(
                operational,
                receipt.receipt_id,
                event="terminal_failure",
                operation_key=operation_key,
                request_digest=request_digest,
                payload_hash=result.transaction_digest,
                recorded_at=timestamp,
            )
            return DecisionConfirmationResultV1(
                status="stale_base",
                decision_digest=decision_digest,
                transaction_digest=result.transaction_digest,
                head_before=challenge.head,
                head_after=result.head_after or challenge.head,
            )
        _append_event(
            operational,
            receipt.receipt_id,
            event="consumed",
            operation_key=operation_key,
            request_digest=request_digest,
            payload_hash=result.transaction_digest,
            recorded_at=timestamp,
        )
        return DecisionConfirmationResultV1(
            status="committed",
            decision_digest=decision_digest,
            transaction_digest=result.transaction_digest,
            head_before=challenge.head,
            head_after=result.head_after,
        )


__all__ = [
    "ApprovalError",
    "HmacTrustedHumanChannel",
    "confirm_decision_with_receipt",
    "create_human_approval_challenge",
    "record_approval_issued",
    "revoke_approval",
]
