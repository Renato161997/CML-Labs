"""Real local TLS and signed-payload regressions for the isolated teaching fixture."""

import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "security_workbench", ROOT / "examples/security/security_workbench.py"
)
workbench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workbench)


class SecurityWorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="owned-cml-security-tests-")
        cls.root = Path(cls.temporary.name).resolve()
        assert cls.root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        workbench.initialize(cls.root)
        cls.server = workbench.FixtureServer(cls.root, 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temporary.cleanup()

    def setUp(self):
        workbench.configure(
            self.root,
            {
                "trust": "root",
                "hostname": "service.lab.example",
                "certificate": "server",
                "token": "reader",
                "feed": "valid",
            },
        )

    def probe(self, mode="tls", operation="read"):
        return workbench.probe(self.root, self.port, mode, operation)

    def test_trusted_certificate_negotiates_real_tls(self):
        result = self.probe()
        self.assertTrue(result["verified"])
        self.assertIn(result["tls"], ("TLSv1.2", "TLSv1.3"))
        self.assertEqual(result["status"], 200)

    def test_unrelated_client_trust_rejects_valid_server(self):
        workbench.configure(self.root, {"trust": "unrelated"})
        self.assertEqual(self.probe(), {"verified": False, "reason": "certificate_not_trusted"})

    def test_wrong_server_hostname_is_rejected(self):
        workbench.configure(self.root, {"certificate": "wrong-name"})
        self.assertEqual(self.probe(), {"verified": False, "reason": "hostname_mismatch"})

    def test_untrusted_server_chain_is_rejected(self):
        workbench.configure(self.root, {"certificate": "untrusted"})
        self.assertEqual(self.probe(), {"verified": False, "reason": "certificate_not_trusted"})

    def test_expired_real_x509_leaf_is_rejected(self):
        workbench.configure(self.root, {"certificate": "expired"})
        self.assertEqual(self.probe(), {"verified": False, "reason": "certificate_expired"})

    def test_reader_cannot_mutate_the_fixture(self):
        before = self.probe("api")
        self.assertEqual(before["status"], 200)
        self.assertEqual(self.probe("api", "disable")["status"], 403)
        self.assertEqual(self.probe("api")["admin_up"], before["admin_up"])

    def test_invalid_token_cannot_read_inventory(self):
        workbench.configure(self.root, {"token": "invalid"})
        self.assertEqual(self.probe("api")["status"], 401)

    def test_admin_change_and_strict_boolean_validation(self):
        workbench.configure(self.root, {"token": "admin"})
        self.assertFalse(self.probe("api", "disable")["admin_up"])
        self.assertEqual(self.probe("api", "invalid-boolean")["status"], 400)
        self.assertFalse(self.probe("api")["admin_up"])
        self.assertTrue(self.probe("api", "enable")["admin_up"])

    def test_tampered_signed_payload_cannot_poison_replay_ledger(self):
        before = (self.root / "seen.json").read_bytes()
        workbench.configure(self.root, {"feed": "tampered"})
        result = self.probe("intel")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "invalid_signature")
        self.assertEqual((self.root / "seen.json").read_bytes(), before)

    def test_signed_but_expired_payload_is_rejected_before_delivery(self):
        before = (self.root / "seen.json").read_bytes()
        workbench.configure(self.root, {"feed": "expired"})
        result = self.probe("intel")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "expired_or_invalid_time")
        self.assertEqual((self.root / "seen.json").read_bytes(), before)

    def test_signature_freshness_replay_and_new_revision_recovery(self):
        self.assertTrue(self.probe("intel")["accepted"])
        self.assertEqual(self.probe("intel")["reason"], "replay")
        workbench.configure(self.root, {"feed": "valid"})
        self.assertTrue(self.probe("intel")["accepted"])


if __name__ == "__main__":
    unittest.main()
