from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.helpers import REPOSITORY_ROOT

from econ_theorist.doctor import doctor_report


class DoctorTests(unittest.TestCase):
    def test_optional_tools_degrade_without_blocking_required_core(self) -> None:
        report = doctor_report()

        self.assertTrue(report["required_ok"])
        self.assertEqual(report["schema"], "econ-theorist/doctor/v1")
        optional = [check for check in report["checks"] if not check["required"]]
        self.assertTrue(optional)
        self.assertTrue(all("impact" in check for check in optional))

    def test_uninitialized_project_is_reported_not_created(self) -> None:
        report = doctor_report(REPOSITORY_ROOT / "tests" / "fixtures")
        project = next(
            check for check in report["checks"] if check["capability"] == "project_store"
        )

        self.assertFalse(project["available"])
        self.assertIn("etai init", project["impact"])

    def test_validator_version_drift_fails_required_capability(self) -> None:
        def version(name: str) -> str | None:
            return "9.9.9" if name == "pydantic" else "2.46.4"

        with patch("econ_theorist.doctor._package_version", side_effect=version):
            report = doctor_report()
        validator = next(
            check
            for check in report["checks"]
            if check["capability"] == "pydantic_models"
        )
        self.assertFalse(report["required_ok"])
        self.assertFalse(validator["available"])
        self.assertIn("differs", validator["impact"])

    def test_missing_enabled_instruction_fails_required_registry_check(self) -> None:
        with patch(
            "econ_theorist.doctor.instruction_bundle_bytes",
            side_effect=FileNotFoundError("missing installed instruction"),
        ):
            report = doctor_report()

        registry = next(
            check
            for check in report["checks"]
            if check["capability"] == "route_registry"
        )
        self.assertFalse(report["required_ok"])
        self.assertFalse(registry["available"])
        self.assertIn("FileNotFoundError", registry["version"])
        self.assertEqual(registry["impact"], "runs cannot begin")


if __name__ == "__main__":
    unittest.main()
