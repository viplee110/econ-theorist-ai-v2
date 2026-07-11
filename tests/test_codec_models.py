"""Unit contracts for strict models and canonical content addressing."""

from __future__ import annotations

import math
import unittest

from pydantic import ValidationError

from tests.helpers import assert_valid_sha256, load_json_bytes, sha256_bytes

from econ_theorist.codec import (
    CanonicalEncodingError,
    canonical_json_bytes,
    object_digest,
    sha256_digest,
    transaction_bytes,
)
from econ_theorist.models import (
    Actor,
    CreateEntityOp,
    EntityVersion,
    FacetPayloads,
    ScientificStatus,
    Transaction,
)


def make_entity(**overrides: object) -> EntityVersion:
    values: dict[str, object] = {
        "entity_id": "ent_project",
        "entity_type": "Project",
        "version": 1,
        "project_id": "prj_contract",
        "title": "Contract fixture",
        "summary": "A minimal canonical entity.",
        "status": ScientificStatus(lifecycle="proposed"),
        "facets": FacetPayloads(),
        "created_at": "2026-07-11T00:00:00Z",
    }
    values.update(overrides)
    return EntityVersion(**values)


def make_transaction(**overrides: object) -> Transaction:
    values: dict[str, object] = {
        "transaction_id": "txn_contract",
        "transaction_schema": 1,
        "origin": "genesis",
        "project_id": "prj_contract",
        "base_revision": None,
        "route_run_id": "run_contract",
        "actor": Actor(kind="agent", actor_id="agent_contract"),
        "intent": "Create the canonical project entity.",
        "operations": (CreateEntityOp(entity=make_entity()),),
        "created_at": "2026-07-11T00:00:01Z",
        "parent_transaction_hash": None,
    }
    values.update(overrides)
    return Transaction(**values)


class CanonicalCodecTests(unittest.TestCase):
    def test_mapping_order_does_not_change_canonical_bytes_or_digest(self) -> None:
        left = {"z": [3, 2, 1], "a": {"unicode": "机制", "active": True}}
        right = {"a": {"active": True, "unicode": "机制"}, "z": [3, 2, 1]}

        left_bytes = canonical_json_bytes(left)
        right_bytes = canonical_json_bytes(right)

        self.assertEqual(left_bytes, right_bytes)
        self.assertEqual(load_json_bytes(left_bytes), left)
        self.assertEqual(object_digest(left), object_digest(right))
        self.assertNotIn(b"\n", left_bytes)

    def test_sha256_digest_is_the_content_address(self) -> None:
        data = b'{"a":1}'
        digest = sha256_digest(data)

        assert_valid_sha256(self, digest)
        self.assertEqual(digest, sha256_bytes(data))

    def test_transaction_digest_is_not_part_of_hashed_bytes(self) -> None:
        transaction = make_transaction()
        data = transaction_bytes(transaction)
        decoded = load_json_bytes(data)
        digest = object_digest(transaction)

        self.assertEqual(digest, sha256_bytes(data))
        self.assertNotIn("digest", decoded)
        self.assertNotIn("transaction_digest", decoded)
        self.assertNotIn(digest.encode("ascii"), data)

    def test_transaction_bytes_fail_closed_on_embedded_digest_fields(self) -> None:
        payload = make_transaction().model_dump(mode="json")
        for forbidden in ("digest", "transaction_digest"):
            with self.subTest(forbidden=forbidden):
                contaminated = dict(payload)
                contaminated[forbidden] = "0" * 64
                with self.assertRaises(CanonicalEncodingError):
                    transaction_bytes(contaminated)

    def test_every_float_is_rejected_including_nested_and_nonfinite(self) -> None:
        values = (
            0.0,
            1.5,
            math.nan,
            math.inf,
            -math.inf,
            {"nested": [1, {"value": 2.0}]},
        )
        for value in values:
            with self.subTest(value=repr(value)):
                with self.assertRaises(CanonicalEncodingError):
                    canonical_json_bytes(value)

    def test_tuple_and_list_have_one_json_representation(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"items": (1, 2, 3)}),
            canonical_json_bytes({"items": [1, 2, 3]}),
        )

    def test_unsupported_python_values_are_rejected(self) -> None:
        for value in ({1, 2}, b"bytes", object()):
            with self.subTest(type=type(value).__name__):
                with self.assertRaises(CanonicalEncodingError):
                    canonical_json_bytes(value)


class StrictModelTests(unittest.TestCase):
    def test_model_rejects_type_coercion(self) -> None:
        payload = make_entity().model_dump(mode="python")
        payload["version"] = "1"

        with self.assertRaises(ValidationError):
            EntityVersion.model_validate(payload)

    def test_model_rejects_unknown_fields(self) -> None:
        payload = make_entity().model_dump(mode="python")
        payload["digest"] = "0" * 64

        with self.assertRaises(ValidationError):
            EntityVersion.model_validate(payload)

    def test_operation_discriminator_is_explicit_in_canonical_bytes(self) -> None:
        decoded = load_json_bytes(transaction_bytes(make_transaction()))

        self.assertEqual(decoded["operations"][0]["op"], "entity.create")


if __name__ == "__main__":  # pragma: no cover - direct test invocation
    unittest.main()
