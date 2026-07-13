from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.machine.bootstrap import (
    BootstrapError,
    build_engine_manifest,
    build_install_plan,
    validate_bootstrap_descriptor,
    verify_engine_inventory,
)
from econ_theorist.machine.models import (
    BootstrapArtifactV1,
    BootstrapDescriptorV1,
)
from econ_theorist.machine.resources import HOST_MANIFEST_V1_HASH


class Phase5ABootstrapTests(unittest.TestCase):
    def _descriptor(self) -> BootstrapDescriptorV1:
        return BootstrapDescriptorV1(
            publisher_id="econ-theorist.release",
            canonical_source="https://github.com/viplee110/econ-theorist-ai-v2",
            release_version="0.1.0-test",
            python_constraint=">=3.11,<3.14",
            supported_platform_tags=("py3-none-any",),
            artifacts=(
                BootstrapArtifactV1(
                    filename="econ_theorist_ai-0.1.0-py3-none-any.whl",
                    sha256="a" * 64,
                    byte_size=123,
                    role="wheel",
                ),
                BootstrapArtifactV1(
                    filename="engine-release-manifest.v1.json",
                    sha256="c" * 64,
                    byte_size=456,
                    role="engine_manifest",
                ),
            ),
            dependency_lock_hash="b" * 64,
            host_manifest_hash=HOST_MANIFEST_V1_HASH,
            engine_manifest_hash="c" * 64,
            issued_at="2026-07-01T00:00:00Z",
            expires_at="2026-08-01T00:00:00Z",
            revocation_policy_id="release-revocations.v1",
            signature_algorithm="external-test-only",
            signature="externally-verified-fixture",
        )

    def test_descriptor_requires_external_trust_and_current_release(self) -> None:
        descriptor = self._descriptor()
        valid, diagnostics = validate_bootstrap_descriptor(
            descriptor,
            trusted_source=descriptor.canonical_source,
            signature_verified_by_external_bootstrap=True,
            revoked=False,
            now="2026-07-13T00:00:00Z",
        )
        self.assertTrue(valid)
        self.assertEqual(diagnostics, ())

        invalid, diagnostics = validate_bootstrap_descriptor(
            descriptor,
            trusted_source="https://example.invalid/fork",
            signature_verified_by_external_bootstrap=False,
            revoked=True,
            now=descriptor.expires_at,
        )
        self.assertFalse(invalid)
        self.assertEqual(
            {item.code for item in diagnostics},
            {
                "canonical_source_mismatch",
                "external_signature_verification_required",
                "release_revoked",
                "descriptor_expired",
            },
        )

    def test_install_plan_keeps_install_and_project_initialization_explicit(self) -> None:
        descriptor = self._descriptor()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            plan = build_install_plan(
                descriptor,
                environment_root=root / "engine",
                absolute_launcher=root / "engine" / "Scripts" / "etai.exe",
                network_origins=("https://files.pythonhosted.org",),
            )
            self.assertTrue(plan.requires_external_bootstrap_executor)
            self.assertFalse(plan.project_initialization_requested)
            self.assertIsNone(plan.project_root)
            self.assertEqual(
                plan.descriptor_hash,
                sha256_digest(canonical_json_bytes(descriptor)),
            )
            with self.assertRaises(BootstrapError):
                build_install_plan(
                    descriptor,
                    environment_root=root / "engine",
                    absolute_launcher=root / "engine" / "etai",
                    network_origins=(),
                )

    def test_source_inventory_is_complete_but_never_claims_release_integrity(self) -> None:
        manifest = build_engine_manifest(launcher_path=sys.executable)
        logical_paths = {
            item.logical_path for item in manifest.release_inventory.resources
        }
        self.assertEqual(manifest.install_mode, "development_checkout")
        self.assertIn("machine/host-manifest.v1.json", logical_paths)
        self.assertIn(
            "schemas/machine/v1/machine-request.schema.json", logical_paths
        )
        distributions = {
            item.name: item for item in manifest.release_inventory.distributions
        }
        self.assertIn("econ-theorist-ai", distributions)
        self.assertTrue(distributions["econ-theorist-ai"].files)
        self.assertEqual(
            manifest.release_inventory_hash,
            sha256_digest(canonical_json_bytes(manifest.release_inventory)),
        )

        _, verification = verify_engine_inventory(
            launcher_path=sys.executable,
            external_bootstrap_verified=True,
        )
        self.assertTrue(verification.verified)
        self.assertEqual(verification.release_integrity, "development_only")

        _, drift = verify_engine_inventory(
            launcher_path=sys.executable,
            expected_manifest_hash="0" * 64,
            external_bootstrap_verified=True,
        )
        self.assertFalse(drift.verified)
        self.assertEqual(drift.release_integrity, "development_only")
        self.assertIn(
            "engine_manifest_mismatch", {item.code for item in drift.diagnostics}
        )


if __name__ == "__main__":
    unittest.main()
