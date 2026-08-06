from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from formal_proof_challenge.deployment.build_hf_space_bundle import build


class FPG3DeploymentTests(unittest.TestCase):
    def test_space_bundle_is_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "space"
            manifest = build(output, "test-revision")
            self.assertEqual(manifest["source_revision"], "test-revision")
            self.assertTrue((output / "README.md").is_file())
            self.assertTrue((output / "Dockerfile").is_file())
            self.assertTrue((output / "formal_proof_challenge" / "app.py").is_file())
            self.assertTrue((output / "formal_proof_challenge" / "anchor.py").is_file())
            stored = json.loads((output / "SPACE_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["manifest_sha256"], manifest["manifest_sha256"])
            self.assertGreater(stored["file_count"], 5)

    def test_bundle_excludes_runtime_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "space"
            build(output)
            self.assertFalse((output / "formal_proof_challenge" / "outputs").exists())
            self.assertFalse(any(path.name == "__pycache__" for path in output.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
