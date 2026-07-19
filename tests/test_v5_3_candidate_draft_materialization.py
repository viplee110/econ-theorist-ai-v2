"""Cold-file regressions for runtime facet-hash candidate drafts."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.candidate_contract import compile_candidate_authoring_contract
from econ_theorist.candidate_draft import (
    CandidateDraftMaterializationError,
    materialize_runtime_facet_hashes,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest, transaction_bytes
from econ_theorist.codex_bridge import CodexBridgeResponseV1
from econ_theorist.machine.completion import (
    CandidateTransactionValidationError,
    candidate_source_digest,
)
from econ_theorist.models import Transaction
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.replay import (
    CandidateValidationError,
    ReferentialIntegrityError,
    replay,
    validate_candidate,
)


_ARCHIVE = (
    REPOSITORY_ROOT
    / "review_outputs"
    / "phase5a2_v5_3_codex_public_pilot"
)


class V53CandidateDraftMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.project_root = Path(cls.temporary.name)
        shutil.copytree(
            _ARCHIVE / "canonical_state" / ".econ-theorist",
            cls.project_root / ".econ-theorist",
        )
        cls.layout = StoreLayout.at(cls.project_root)
        cls.snapshot = replay(cls.layout)
        cls.response = CodexBridgeResponseV1.model_validate_json(
            (_ARCHIVE / "run" / "009_resume_stdout.json").read_bytes(),
            strict=True,
        )
        assert cls.response.work_packet is not None
        assert cls.response.candidate_authoring_contract is not None
        cls.packet = cls.response.work_packet
        cls.archived_contract = cls.response.candidate_authoring_contract
        cls.archived_raw = json.loads(
            (_ARCHIVE / "run" / "010_candidate_attempt1.json").read_text(
                encoding="utf-8"
            )
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def _candidate_path(self) -> Path:
        path = self.project_root / self.packet.candidate_logical_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _governs_relation(self, raw: dict[str, object]) -> dict[str, object]:
        relations = [
            operation["relation"]
            for operation in raw["operations"]  # type: ignore[index]
            if operation.get("op") in {  # type: ignore[union-attr]
                "relation.create",
                "relation.supersede",
            }
            and operation["relation"].get("relation_type") == "governs"  # type: ignore[index,union-attr]
        ]
        self.assertEqual(len(relations), 1)
        return relations[0]  # type: ignore[return-value]

    def _draft(self) -> dict[str, object]:
        raw = copy.deepcopy(self.archived_raw)
        governs = self._governs_relation(raw)
        governs["upstream"]["semantic_hash"] = None  # type: ignore[index]
        return raw

    def _write(self, raw: dict[str, object]) -> Path:
        path = self._candidate_path()
        path.write_bytes(canonical_json_bytes(raw) + b"\n")
        return path

    def test_cold_serialized_draft_has_one_canonical_identity_and_is_not_rewritten(
        self,
    ) -> None:
        raw = self._draft()
        path = self._write(raw)
        source_before = path.read_bytes()
        materialized = materialize_runtime_facet_hashes(
            source_before,
            self.archived_contract,
        )
        self.assertIsNotNone(materialized)
        assert materialized is not None
        canonical = Transaction.model_validate_json(materialized, strict=True)
        expected = sha256_digest(transaction_bytes(canonical))

        first = candidate_source_digest(self.layout, self.packet, path)
        second = candidate_source_digest(self.layout, self.packet, path)
        self.assertEqual(first, expected)
        self.assertEqual(second, expected)
        self.assertEqual(path.read_bytes(), source_before)

        explicit_path = self._write(json.loads(materialized))
        self.assertEqual(
            candidate_source_digest(self.layout, self.packet, explicit_path),
            expected,
        )

    def test_archived_candidate_reaches_the_first_scientific_diagnostic_after_hash(
        self,
    ) -> None:
        materialized = materialize_runtime_facet_hashes(
            canonical_json_bytes(self._draft()),
            self.archived_contract,
        )
        assert materialized is not None
        candidate = Transaction.model_validate_json(materialized, strict=True)
        with self.assertRaisesRegex(
            CandidateValidationError,
            "active_margin_witness_missing",
        ):
            validate_candidate(
                self.snapshot,
                candidate,
                route_registry_hash=self.packet.route_registry_hash,
                enforce_live_current_policy=True,
            )

        wrong = Transaction.model_validate_json(
            canonical_json_bytes(self.archived_raw),
            strict=True,
        )
        with self.assertRaisesRegex(
            ReferentialIntegrityError,
            "incorrect upstream semantic hash",
        ):
            validate_candidate(
                self.snapshot,
                wrong,
                route_registry_hash=self.packet.route_registry_hash,
                enforce_live_current_policy=True,
            )

    def test_null_is_materialized_only_at_one_exact_runtime_template(self) -> None:
        unrelated = self._draft()
        audit = next(
            operation["relation"]
            for operation in unrelated["operations"]  # type: ignore[index]
            if operation.get("op") == "relation.create"  # type: ignore[union-attr]
            and operation["relation"].get("relation_type") == "audits"  # type: ignore[index,union-attr]
        )
        audit["upstream"]["semantic_hash"] = None
        with self.assertRaises(CandidateTransactionValidationError) as unrelated_error:
            candidate_source_digest(
                self.layout,
                self.packet,
                self._write(unrelated),
            )
        self.assertTrue(
            any(
                item["location"][-1:] == ["semantic_hash"]
                for item in unrelated_error.exception.issues
            )
        )

        wrong_topology = self._draft()
        governs = self._governs_relation(wrong_topology)
        governs["target"]["entity_id"] = "dossier.wrong.target"  # type: ignore[index]
        with self.assertRaises(CandidateTransactionValidationError) as missing:
            candidate_source_digest(
                self.layout,
                self.packet,
                self._write(wrong_topology),
            )
        self.assertEqual(
            missing.exception.issues[0]["type"],
            "candidate_draft_template_missing",
        )

        duplicated = self._draft()
        governs_operation = next(
            operation
            for operation in duplicated["operations"]  # type: ignore[index]
            if operation.get("op") == "relation.create"  # type: ignore[union-attr]
            and operation["relation"].get("relation_type") == "governs"  # type: ignore[index,union-attr]
        )
        duplicate_operation = copy.deepcopy(governs_operation)
        duplicate_operation["relation"]["relation_id"] = "relation.duplicate.governs"
        duplicated["operations"].insert(-1, duplicate_operation)  # type: ignore[index,union-attr]
        with self.assertRaises(CandidateTransactionValidationError) as duplicate:
            candidate_source_digest(
                self.layout,
                self.packet,
                self._write(duplicated),
            )
        self.assertEqual(
            duplicate.exception.issues[0]["type"],
            "candidate_draft_template_duplicated",
        )

    def test_missing_template_reports_nearest_relation_exact_field(self) -> None:
        raw = self._draft()
        governs_operation_index, governs_operation = next(
            (index, operation)
            for index, operation in enumerate(raw["operations"])  # type: ignore[index]
            if operation.get("op") == "relation.create"  # type: ignore[union-attr]
            and operation["relation"].get("relation_type") == "governs"  # type: ignore[index,union-attr]
        )
        governs_operation["relation"]["downstream"]["semantic_hash"] = None

        with self.assertRaises(CandidateDraftMaterializationError) as captured:
            materialize_runtime_facet_hashes(
                canonical_json_bytes(raw),
                self.archived_contract,
            )

        error = captured.exception
        expected_location = (
            "operations",
            governs_operation_index,
            "relation",
            "downstream",
            "semantic_hash",
        )
        self.assertEqual(error.issue_type, "candidate_draft_template_missing")
        self.assertEqual(error.location, expected_location)
        self.assertEqual(
            error.json_pointer,
            f"/operations/{governs_operation_index}/relation/downstream/semantic_hash",
        )
        self.assertEqual(error.mismatch_kind, "extra field")
        self.assertEqual(error.expected, "<absent>")
        self.assertEqual(error.observed, "<present>")
        self.assertIn("extra field", error.message)
        self.assertIn(
            "expected \"<absent>\", observed \"<present>\"",
            error.message,
        )

        with self.assertRaises(CandidateTransactionValidationError) as routed:
            candidate_source_digest(
                self.layout,
                self.packet,
                self._write(raw),
            )
        issue = routed.exception.issues[0]
        self.assertEqual(issue["json_pointer"], error.json_pointer)
        self.assertEqual(issue["expected"], error.expected)
        self.assertEqual(issue["observed"], error.observed)
        self.assertEqual(issue["mismatch_kind"], error.mismatch_kind)

    def test_nearest_relation_distinguishes_missing_and_mismatched_fields(self) -> None:
        for mismatch_kind in ("missing field", "mismatched field"):
            with self.subTest(mismatch_kind=mismatch_kind):
                raw = self._draft()
                governs = self._governs_relation(raw)
                downstream = governs["downstream"]
                expected_facet = downstream["facet"]
                if mismatch_kind == "missing field":
                    del downstream["facet"]
                    observed = "<missing>"
                else:
                    downstream["facet"] = "wrong_facet"
                    observed = "wrong_facet"

                with self.assertRaises(
                    CandidateDraftMaterializationError
                ) as captured:
                    materialize_runtime_facet_hashes(
                        canonical_json_bytes(raw),
                        self.archived_contract,
                    )

                error = captured.exception
                self.assertEqual(error.location[-2:], ("downstream", "facet"))
                self.assertEqual(error.mismatch_kind, mismatch_kind)
                self.assertEqual(error.expected, expected_facet)
                self.assertEqual(error.observed, observed)

    def test_nearest_relation_stays_generic_for_multiple_differences(self) -> None:
        raw = self._draft()
        governs = self._governs_relation(raw)
        governs["downstream"]["semantic_hash"] = None  # type: ignore[index]
        governs["downstream"]["facet"] = "wrong_facet"  # type: ignore[index]

        with self.assertRaises(CandidateDraftMaterializationError) as captured:
            materialize_runtime_facet_hashes(
                canonical_json_bytes(raw),
                self.archived_contract,
            )

        error = captured.exception
        self.assertEqual(error.location, ("operations",))
        self.assertIsNone(error.mismatch_kind)
        self.assertNotIn("Closest relation", error.message)

    def test_nearest_relation_stays_generic_when_best_candidates_tie(self) -> None:
        raw = self._draft()
        governs_operation = next(
            operation
            for operation in raw["operations"]  # type: ignore[index]
            if operation.get("op") == "relation.create"  # type: ignore[union-attr]
            and operation["relation"].get("relation_type") == "governs"  # type: ignore[index,union-attr]
        )
        governs_operation["relation"]["downstream"]["semantic_hash"] = None
        tied_operation = copy.deepcopy(governs_operation)
        del tied_operation["relation"]["downstream"]["semantic_hash"]
        tied_operation["relation"]["downstream"]["facet"] = "wrong_facet"
        tied_operation["relation"]["relation_id"] = "relation.tied.governs"
        raw["operations"].insert(-1, tied_operation)  # type: ignore[index,union-attr]

        with self.assertRaises(CandidateDraftMaterializationError) as captured:
            materialize_runtime_facet_hashes(
                canonical_json_bytes(raw),
                self.archived_contract,
            )

        error = captured.exception
        self.assertEqual(error.location, ("operations",))
        self.assertIsNone(error.mismatch_kind)

    def test_near_match_float_observation_is_canonical_safe(self) -> None:
        raw = self._draft()
        governs = self._governs_relation(raw)
        governs["downstream"]["facet"] = 1.5  # type: ignore[index]
        source = json.dumps(raw, ensure_ascii=True, allow_nan=False).encode("utf-8")

        with self.assertRaises(CandidateDraftMaterializationError) as captured:
            materialize_runtime_facet_hashes(source, self.archived_contract)

        error = captured.exception
        self.assertEqual(error.observed, "1.5 (float)")
        canonical_json_bytes(
            {
                "json_pointer": error.json_pointer,
                "message": error.message,
                "observed": error.observed,
            }
        )

    def test_near_match_surrogate_key_is_bounded_and_utf8_safe(self) -> None:
        raw = self._draft()
        governs = self._governs_relation(raw)
        governs["downstream"]["\ud800"] = "private candidate text"  # type: ignore[index]
        source = json.dumps(raw, ensure_ascii=True, allow_nan=False).encode("utf-8")

        with self.assertRaises(CandidateDraftMaterializationError) as captured:
            materialize_runtime_facet_hashes(source, self.archived_contract)

        error = captured.exception
        self.assertEqual(error.observed, "<present>")
        self.assertNotIn("private candidate text", error.message)
        canonical_json_bytes(
            {
                "json_pointer": error.json_pointer,
                "message": error.message,
                "observed": error.observed,
            }
        )

    def test_route_boundary_preserves_archived_v6_contract(self) -> None:
        archived_packet_hash = sha256_digest(canonical_json_bytes(self.packet))
        reconstructed = compile_candidate_authoring_contract(
            self.layout,
            self.packet,
            archived_packet_hash,
        )
        self.assertEqual(
            canonical_json_bytes(reconstructed),
            canonical_json_bytes(self.archived_contract),
        )
        self.assertIsNone(reconstructed.candidate_draft_semantics)

        current_packet = self.packet.model_copy(
            update={"engine_semantics_hash": "f" * 64}
        )
        current = compile_candidate_authoring_contract(
            self.layout,
            current_packet,
            sha256_digest(canonical_json_bytes(current_packet)),
        )
        self.assertIsNone(current.candidate_draft_semantics)
        semantic_hash_schema = current.transaction_json_schema["$defs"][
            "SemanticFacetRef"
        ]["properties"]["semantic_hash"]
        self.assertEqual(semantic_hash_schema.get("type"), "string")
        self.assertTrue(
            any(
                "compute econ_theorist.runtime.freshness.facet_semantic_hash"
                in instruction
                for instruction in current.authoring_instructions
            )
        )

    def test_archived_v5_public_contract_schema_projection_is_byte_stable(
        self,
    ) -> None:
        archive = (
            REPOSITORY_ROOT
            / "review_outputs"
            / "phase5a2_v5_2_codex_public_pilot"
        )
        response = CodexBridgeResponseV1.model_validate_json(
            (
                archive
                / "run"
                / "011_continue_after_decompose_stdout.jsonl"
            ).read_bytes(),
            strict=True,
        )
        assert response.work_packet is not None
        assert response.candidate_authoring_contract is not None
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory)
            shutil.copytree(
                archive / "canonical_store" / ".econ-theorist",
                project_root / ".econ-theorist",
            )
            packet = response.work_packet
            # Isolate the public/schema projection from the retired v5 route
            # entry predicate.  This is not an unfinished-run resume claim;
            # executable cold retry support begins with archived v6.
            with patch(
                "econ_theorist.runs.validate_phase5_route_entry",
                return_value=None,
            ):
                reconstructed = compile_candidate_authoring_contract(
                    StoreLayout.at(project_root),
                    packet,
                    sha256_digest(canonical_json_bytes(packet)),
                )
        self.assertEqual(
            canonical_json_bytes(reconstructed),
            canonical_json_bytes(response.candidate_authoring_contract),
        )
        bundle_schema = next(
            item.payload_json_schema
            for item in reconstructed.payload_schemas
            if item.entity_type == "FramingQualityBundle"
        )
        self.assertEqual(
            sha256_digest(canonical_json_bytes(bundle_schema)),
            "2fa6ef58bf94b98768e76d8c348ce6efdf7779f7e3d54d95367493493a594beb",
        )


if __name__ == "__main__":
    unittest.main()
