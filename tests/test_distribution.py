"""Resource resolution and an opt-in, offline distribution integration check."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from storyforge import resources
from storyforge.util import ROOT


class ResourceResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.checkout = Path(self.temp.name) / "checkout"
        self.package = self.checkout / "storyforge"
        self.package.mkdir(parents=True)
        self.module = self.package / "resources.py"
        self.module.touch()

    def populate(self, directory: Path) -> None:
        for name in resources._MARKERS:
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("resource fixture\n", encoding="utf-8")

    def test_checkout_and_editable_install_use_canonical_resources(self) -> None:
        self.populate(self.checkout)
        (self.checkout / "pyproject.toml").touch()
        with patch.object(resources, "__file__", str(self.module)):
            self.assertEqual(resources.resource_root(), self.checkout.resolve())

    def test_wheel_uses_its_own_resources_even_beside_another_checkout(self) -> None:
        self.populate(self.checkout)
        (self.checkout / "pyproject.toml").touch()
        bundle = self.package / "_resources"
        self.populate(bundle)
        with patch.object(resources, "__file__", str(self.module)):
            self.assertEqual(resources.resource_root(), bundle.resolve())

    def test_incomplete_bundle_is_reported_instead_of_using_unrelated_resources(self) -> None:
        self.populate(self.checkout)
        (self.checkout / "pyproject.toml").touch()
        (self.package / "_resources").mkdir()
        with patch.object(resources, "__file__", str(self.module)):
            with self.assertRaisesRegex(RuntimeError, "bundled resources are incomplete"):
                resources.resource_root()

    def test_missing_installation_has_an_actionable_error(self) -> None:
        with patch.object(resources, "__file__", str(self.module)):
            with self.assertRaisesRegex(RuntimeError, "pip or pipx"):
                resources.resource_root()

    def test_legacy_root_remains_the_resource_directory(self) -> None:
        self.assertEqual(ROOT, resources.resource_root())
        self.assertTrue((ROOT / "renderer" / "package-lock.json").is_file())


@unittest.skipUnless(
    os.environ.get("STORYFORGE_TEST_DISTRIBUTION") == "1",
    "Run python scripts/verify_distribution.py for the full wheel/sdist integration check",
)
class DistributionTests(unittest.TestCase):
    def test_both_distribution_formats_install_without_a_checkout(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "scripts" / "verify_distribution.py")],
            cwd=root, text=True, capture_output=True, timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
