import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "examples/management"))
import embed_webhook
import ssh_probe


class EmbeddedProfileTests(unittest.TestCase):
    def prepare(self, root, profile, files):
        (root / "catalog").mkdir()
        (root / "labs").mkdir()
        (root / "catalog/curated.json").write_text(
            json.dumps({"labs/example.yaml": {"example_profile": profile}}), encoding="utf-8"
        )
        cloud = yaml.safe_dump({"write_files": files})
        path = root / "labs/example.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "nodes": [
                        {
                            "node_definition": "ubuntu",
                            "configuration": [{"name": "user-data", "content": cloud}],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_unknown_profile_and_missing_source_fail_closed(self):
        for profile in ("../../private-file", "ssh-management"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.prepare(root, profile, [])
                with patch.object(embed_webhook, "ROOT", root), self.assertRaises(ValueError):
                    embed_webhook.update(check=True)

    def test_stale_embedded_source_is_detected_without_mutating_check_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "examples/management/ssh_probe.py"
            source.parent.mkdir(parents=True)
            source.write_text("print('new source')\n", encoding="utf-8")
            path = self.prepare(
                root,
                "ssh-management",
                [{"path": "/opt/cml-management/ssh_probe.py", "encoding": "b64", "content": "old"}],
            )
            before = path.read_bytes()
            with patch.object(embed_webhook, "ROOT", root):
                self.assertEqual(embed_webhook.update(check=True), ["labs/example.yaml"])
            self.assertEqual(path.read_bytes(), before)

    def test_ssh_probe_refuses_a_destination_outside_the_lab_before_connecting(self):
        with (
            patch.object(sys, "argv", ["ssh_probe.py", "--host", "203.0.113.1"]),
            patch.object(ssh_probe, "session") as session,
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            ssh_probe.main()
        self.assertEqual(raised.exception.code, 2)
        session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
