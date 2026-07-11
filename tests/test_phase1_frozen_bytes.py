"""Byte-level compatibility oracle for the frozen Phase 1 v1 substrate."""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import (
    canonical_json_bytes,
    sha256_digest,
    transaction_bytes,
)
from econ_theorist.models import ContextManifest, RouteRun, Transaction
from econ_theorist.policy import (
    ROUTE_REGISTRY_V1_HASH,
    load_route_registry_by_hash,
    registry_hash,
)
from econ_theorist.runs import (
    compiled_context_path,
    context_path,
    provenance_bytes,
    read_compiled_context,
    read_context,
    run_directory,
    run_path,
)
from econ_theorist.runtime import HeadStore, ObjectStore, StoreLayout, replay


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "phase1_frozen_v1"
FIXTURE_BUNDLE = FIXTURE_ROOT / "canonical_bytes.v1.json"

# These are independent review anchors.  Do not regenerate them from the
# current serializer and do not update them to make a changed serializer pass.
EXPECTED_BYTES = {
    "genesis_transaction": (
        1362,
        "717c037bbc9fa38e403b4de4c59790898fb58eaa1b0a6760066ad0f721ee037e",
    ),
    "framing_run": (
        616,
        "60b0fd7c0f4641837406fb4a0d700285d8655fa4322c25844485f2d993b1f73e",
    ),
    "framing_manifest": (
        1356,
        "358d85b700895b43958701d346919b19324401ba0cdba3d606a567a5d170a1b6",
    ),
    "framing_compiled_context": (
        2762,
        "fa1e3dc8acba5e40228e9430cb0df5ea802116196f24c75dbdcc27b2c66c6c1a",
    ),
    "framing_transaction": (
        1679,
        "bc39706b06541436b0bc75dcd09933e3f1e423717a92e4e1d98f2501dcd52900",
    ),
}


def _fixture_payloads() -> dict[str, bytes]:
    bundle = json.loads(FIXTURE_BUNDLE.read_text(encoding="utf-8"))
    if bundle != {
        "encoding": "base64",
        "fixture_schema": 1,
        "payloads": bundle.get("payloads"),
    }:
        raise AssertionError("unexpected Phase 1 frozen-byte bundle envelope")
    encoded = bundle["payloads"]
    if not isinstance(encoded, dict) or set(encoded) != set(EXPECTED_BYTES):
        raise AssertionError("Phase 1 frozen-byte bundle has unexpected payloads")
    try:
        return {
            name: base64.b64decode(value, validate=True)
            for name, value in encoded.items()
        }
    except (TypeError, ValueError) as exc:
        raise AssertionError("Phase 1 frozen-byte bundle is not strict base64") from exc


class Phase1FrozenBytesTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.layout = StoreLayout.at(temporary.name).ensure()
        self.payloads = _fixture_payloads()

    def _install_genesis(self) -> str:
        data = self.payloads["genesis_transaction"]
        digest = EXPECTED_BYTES["genesis_transaction"][1]
        ObjectStore(self.layout).install_bytes("transactions", digest, data)
        HeadStore(self.layout).replace(None, digest)
        return digest

    def test_frozen_bytes_are_canonical_and_hash_pinned(self) -> None:
        self.assertEqual(
            ROUTE_REGISTRY_V1_HASH,
            "d9c84001420bd63a82418ee3cfe1776895be69936e921aa8c4790a8966aa6913",
        )
        self.assertEqual(
            registry_hash(load_route_registry_by_hash(ROUTE_REGISTRY_V1_HASH)),
            ROUTE_REGISTRY_V1_HASH,
        )
        for name, (expected_size, expected_digest) in EXPECTED_BYTES.items():
            with self.subTest(payload=name):
                data = self.payloads[name]
                self.assertEqual(len(data), expected_size)
                self.assertEqual(sha256_digest(data), expected_digest)

        genesis = Transaction.model_validate_json(
            self.payloads["genesis_transaction"], strict=True
        )
        framing = Transaction.model_validate_json(
            self.payloads["framing_transaction"], strict=True
        )
        run = RouteRun.model_validate_json(self.payloads["framing_run"], strict=True)
        manifest = ContextManifest.model_validate_json(
            self.payloads["framing_manifest"], strict=True
        )
        compiled = json.loads(
            self.payloads["framing_compiled_context"].decode("utf-8")
        )

        self.assertEqual(transaction_bytes(genesis), self.payloads["genesis_transaction"])
        self.assertEqual(transaction_bytes(framing), self.payloads["framing_transaction"])
        self.assertEqual(canonical_json_bytes(run), self.payloads["framing_run"])
        self.assertEqual(canonical_json_bytes(manifest), self.payloads["framing_manifest"])
        self.assertEqual(
            canonical_json_bytes(compiled),
            self.payloads["framing_compiled_context"],
        )
        self.assertEqual(manifest.route_registry_hash, ROUTE_REGISTRY_V1_HASH)
        self.assertEqual(framing.route_run_hash, EXPECTED_BYTES["framing_run"][1])
        self.assertEqual(
            framing.context_manifest_hash,
            EXPECTED_BYTES["framing_manifest"][1],
        )
        self.assertEqual(
            framing.compiled_context_hash,
            EXPECTED_BYTES["framing_compiled_context"][1],
        )

    def test_frozen_context_reads_and_recompiles_byte_exactly(self) -> None:
        self._install_genesis()
        base = replay(self.layout)
        self.assertEqual(base.head, EXPECTED_BYTES["genesis_transaction"][1])

        run_id = "run.phase1.frozen.frame"
        run_directory(self.layout, run_id).mkdir(parents=True)
        run_path(self.layout, run_id).write_bytes(self.payloads["framing_run"])
        context_path(self.layout, run_id).write_bytes(
            self.payloads["framing_manifest"]
        )
        compiled_context_path(self.layout, run_id).write_bytes(
            self.payloads["framing_compiled_context"]
        )

        manifest = read_context(self.layout, run_id)
        compiled = read_compiled_context(self.layout, run_id)
        self.assertEqual(
            canonical_json_bytes(manifest), self.payloads["framing_manifest"]
        )
        self.assertEqual(
            canonical_json_bytes(compiled),
            self.payloads["framing_compiled_context"],
        )
        self.assertEqual(
            provenance_bytes(self.layout, run_id),
            {
                "run": self.payloads["framing_run"],
                "manifest": self.payloads["framing_manifest"],
                "context": self.payloads["framing_compiled_context"],
            },
        )

    def test_frozen_route_transaction_replays_without_rewriting_bytes(self) -> None:
        genesis_digest = self._install_genesis()
        store = ObjectStore(self.layout)
        for name in (
            "framing_run",
            "framing_manifest",
            "framing_compiled_context",
        ):
            digest = EXPECTED_BYTES[name][1]
            store.install_bytes("provenance", digest, self.payloads[name])

        route_digest = EXPECTED_BYTES["framing_transaction"][1]
        store.install_bytes(
            "transactions", route_digest, self.payloads["framing_transaction"]
        )
        HeadStore(self.layout).replace(genesis_digest, route_digest)

        snapshot = replay(self.layout)
        self.assertEqual(snapshot.head, route_digest)
        self.assertEqual(snapshot.chain, (genesis_digest, route_digest))
        self.assertEqual(
            snapshot.transaction_ids,
            (
                "transaction.phase1.frozen.genesis",
                "transaction.phase1.frozen.frame",
            ),
        )
        self.assertEqual(snapshot.current_entities["project.phase1.frozen.bytes"], 1)
        self.assertEqual(snapshot.current_entities["question.phase1.frozen"], 1)
        self.assertEqual(
            store.read_bytes("transactions", route_digest),
            self.payloads["framing_transaction"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
