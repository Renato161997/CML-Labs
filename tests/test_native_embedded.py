import base64
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import embed_webhook


class NativeEmbeddedSourcesTest(unittest.TestCase):
    def topology(self, payload):
        content = (
            "ip link set eth1 up\nbase64 -d > /lab/snmp_probe.py "
            "<<'CML_EMBED_EXAMPLES_MANAGEMENT_SNMP_PROBE_PY'\n"
            + base64.b64encode(payload).decode()
            + "\nCML_EMBED_EXAMPLES_MANAGEMENT_SNMP_PROBE_PY\necho READY\n"
        )
        return {
            "nodes": [
                {"label": "TOOLS", "configuration": [{"name": "boot.sh", "content": content}]}
            ]
        }

    def test_drift_is_repaired_without_changing_network_setup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "examples/management/snmp_probe.py"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"current-source\n")
            data = self.topology(b"old-source\n")
            with patch.object(embed_webhook, "ROOT", root):
                self.assertTrue(
                    embed_webhook.native_sources(data, {"example_profile": "native-snmp"})
                )
                self.assertFalse(
                    embed_webhook.native_sources(data, {"example_profile": "native-snmp"})
                )
            boot = data["nodes"][0]["configuration"][0]["content"]
            self.assertTrue(boot.startswith("ip link set eth1 up\n"))
            self.assertTrue(boot.endswith("\necho READY\n"))

    def test_missing_registered_node_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "node"):
            embed_webhook.native_sources({"nodes": []}, {"example_profile": "native-snmp"})

    def test_unknown_or_removed_profile_cannot_skip_embedded_source(self):
        for metadata in ({}, {"example_profile": "native-typo"}):
            with self.subTest(metadata=metadata), self.assertRaisesRegex(ValueError, "registered"):
                embed_webhook.native_sources(self.topology(b"script\n"), metadata)

    def test_missing_payload_cannot_silently_skip_source_verification(self):
        data = self.topology(b"script\n")
        data["nodes"][0]["configuration"][0]["content"] = "echo READY\n"
        with self.assertRaisesRegex(ValueError, "payload"):
            embed_webhook.native_sources(data, {"example_profile": "native-snmp"})
