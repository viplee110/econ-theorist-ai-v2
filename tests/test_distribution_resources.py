from __future__ import annotations

import importlib.metadata
from pathlib import Path, PurePosixPath
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist import distribution_resources
from econ_theorist.distribution_resources import DistributionResourceError


class _FakeDistribution:
    def __init__(self, site_packages: Path, entries: tuple[str, ...]) -> None:
        self.site_packages = site_packages
        self.files = tuple(PurePosixPath(entry) for entry in entries)

    def locate_file(self, entry: object) -> Path:
        return self.site_packages / Path(str(entry))


class DistributionResourceTests(unittest.TestCase):
    def tearDown(self) -> None:
        distribution_resources.installed_resource_root.cache_clear()

    def _fake_distribution(
        self,
        temporary_root: Path,
        entries: tuple[str, ...],
    ) -> tuple[_FakeDistribution, Path]:
        environment = temporary_root / "environment"
        site_packages = environment / "Lib" / "site-packages"
        site_packages.mkdir(parents=True)
        root = environment / "share" / "econ-theorist"
        for entry in entries:
            target = (site_packages / Path(entry)).resolve(strict=False)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"resource")
        return _FakeDistribution(site_packages, entries), root

    def test_installed_resource_root_uses_record_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fake, expected = self._fake_distribution(
                Path(temporary_directory),
                (
                    "../../share/econ-theorist/routes/registry.v4.json",
                    "../../share/econ-theorist/machine/host-manifest.v1.json",
                ),
            )
            with patch.object(importlib.metadata, "distribution", return_value=fake):
                actual = distribution_resources.installed_resource_root()

            self.assertEqual(actual, expected.resolve())

    def test_installed_resource_root_rejects_multiple_record_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fake, _ = self._fake_distribution(
                Path(temporary_directory),
                (
                    "../../share/econ-theorist/routes/registry.v4.json",
                    "../../../share/econ-theorist/machine/host-manifest.v1.json",
                ),
            )
            with patch.object(importlib.metadata, "distribution", return_value=fake):
                with self.assertRaisesRegex(DistributionResourceError, "multiple"):
                    distribution_resources.installed_resource_root()

    def test_installed_resource_root_requires_record_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fake = _FakeDistribution(
                Path(temporary_directory)
                / "environment"
                / "Lib"
                / "site-packages",
                ("econ_theorist/__init__.py",),
            )
            with patch.object(importlib.metadata, "distribution", return_value=fake):
                with self.assertRaisesRegex(
                    DistributionResourceError, "does not inventory"
                ):
                    distribution_resources.installed_resource_root()

    def test_all_frozen_schema_namespaces_are_data_files(self) -> None:
        configuration = tomllib.loads(
            (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        data_files = configuration["tool"]["setuptools"]["data-files"]
        namespaces = {
            "schemas/v1": "share/econ-theorist/schemas/v1",
            "schemas/theory/v1": "share/econ-theorist/schemas/theory/v1",
            "schemas/authoring/v1": "share/econ-theorist/schemas/authoring/v1",
            "schemas/profile_craft/v1": (
                "share/econ-theorist/schemas/profile_craft/v1"
            ),
        }
        for source_namespace, installed_namespace in namespaces.items():
            expected = {
                path.relative_to(REPOSITORY_ROOT).as_posix()
                for path in (REPOSITORY_ROOT / source_namespace).glob(
                    "*.schema.json"
                )
            }
            self.assertTrue(expected)
            self.assertEqual(set(data_files[installed_namespace]), expected)

    def test_active_v7_policy_resources_are_packaged(self) -> None:
        configuration = tomllib.loads(
            (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        data_files = configuration["tool"]["setuptools"]["data-files"]
        self.assertIn(
            "routes/registry.v6.json",
            data_files["share/econ-theorist/routes"],
        )
        self.assertIn(
            "routes/instructions/audit.framing_economics.v6.txt",
            data_files["share/econ-theorist/routes/instructions"],
        )
        self.assertIn(
            "machine/navigation-registry.v5.json",
            data_files["share/econ-theorist/machine"],
        )
        self.assertIn(
            "routes/registry.v7.json",
            data_files["share/econ-theorist/routes"],
        )
        self.assertIn(
            "routes/instructions/audit.framing_economics.v7.txt",
            data_files["share/econ-theorist/routes/instructions"],
        )
        self.assertIn(
            "machine/navigation-registry.v6.json",
            data_files["share/econ-theorist/machine"],
        )


if __name__ == "__main__":
    unittest.main()
