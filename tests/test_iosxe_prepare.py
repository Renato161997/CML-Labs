import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from acceptance import execute_plan, validate_plan
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from iosxe_prepare import (
    OPERATION,
    enroll_selfsigned,
    implementation_digest,
    match_scanned_key,
    rsa_public_keys,
    select_certificate,
    upload_public_file,
)
from labtools import check_evidence


class IosxeTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.now = datetime.now(UTC)

    def certificate(self, san=True, expired=False):
        name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "api.cml-lab.example")])
        builder = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(self.key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=2))
            .not_valid_after(self.now + timedelta(days=-1 if expired else 1))
        )
        if san:
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.DNSName("api.cml-lab.example")]), critical=False
            )
        return (
            builder.sign(self.key, hashes.SHA256())
            .public_bytes(serialization.Encoding.PEM)
            .decode()
        )

    def test_duplicate_export_is_accepted_but_ambiguous_certificates_are_not(self):
        first, second = self.certificate(), self.certificate()
        self.assertEqual(select_certificate(first + first, self.now), first)
        with self.assertRaises(ValueError):
            select_certificate(first + second, self.now)

    def test_missing_san_and_expired_certificate_are_rejected(self):
        for pem in (self.certificate(san=False), self.certificate(expired=True)):
            with self.assertRaises(ValueError):
                select_certificate(pem, self.now)

    def test_short_final_hex_word_and_strict_serial_pin(self):
        raw = self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        words = [raw.hex()[i : i + 8] for i in range(0, len(raw.hex()), 8)]
        self.assertEqual(len(words[-1]), 4)
        output = (
            "Key name: LABSSH\nKey Data:\n"
            + "\n".join("  " + " ".join(words[i : i + 8]) for i in range(0, len(words), 8))
            + "\nAPI#\n"
        )
        pub = (
            self.key.public_key()
            .public_bytes(serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH)
            .decode()
        )
        trusted = rsa_public_keys(output)
        self.assertEqual(trusted, {pub})
        line = "[198.18.0.1]:830 " + pub + "\n"
        self.assertEqual(match_scanned_key(line + line, trusted), pub.split()[1])
        with self.assertRaises(ValueError):
            match_scanned_key(line, set())
        with self.assertRaises(ValueError):
            rsa_public_keys(output.replace(words[-1], ""))

    def test_unexpected_dialogue_never_receives_a_yes(self):
        console = Mock(label="API")
        console.read.return_value = "API(config)#crypto pki enroll LABTLS\nUnexpected confirmation?"
        with self.assertRaises(ValueError):
            enroll_selfsigned(console)
        self.assertEqual(console.send_raw.call_count, 1)
        self.assertNotIn("yes\r", [call.args[0] for call in console.send_raw.call_args_list])

    def test_public_material_cannot_be_written_to_an_arbitrary_path(self):
        console = Mock()
        with self.assertRaises(ValueError):
            upload_public_file(console, "/etc/passwd", "untrusted")
        console.send_raw.assert_not_called()

    def test_stale_preparation_is_rejected_before_any_console_action(self):
        plan = {
            "prepare": [
                {
                    "operation": OPERATION,
                    "router": "API",
                    "client": "TOOLS",
                    "implementation_sha256": "0" * 64,
                }
            ],
            "checks": [
                {
                    "node": "API",
                    "command": "show version",
                    "pattern": "IOS",
                    "expectation": "Actual IOS version",
                }
            ],
        }
        self.assertTrue(validate_plan(plan, {"API", "TOOLS"}))
        console = Mock()
        with self.assertRaises(ValueError):
            execute_plan(plan, console, Mock())
        console.assert_not_called()

    def test_green_evidence_cannot_omit_preparation_or_use_the_wrong_implementation(self):
        digest = implementation_digest()
        prepare = {
            "operation": OPERATION,
            "router": "API",
            "client": "TOOLS",
            "implementation_sha256": digest,
        }
        plan = {"prepare": [prepare], "checks": [{"node": "API", "command": "show version"}]}
        proof = {
            "sha256": "source",
            "status": "passed",
            "test_lab_removed": True,
            "cml_version": "2.10.1",
            "checks": [{"node": "API", "command": "show version", "passed": True}],
        }
        self.assertTrue(check_evidence(proof, "fixture", "source", "runtime", expected_plan=plan))
        proof["checks"].append(
            {
                "phase": "prepare",
                "kind": "preparation",
                "node": "API",
                "command": OPERATION,
                "implementation_sha256": "wrong",
                "passed": True,
            }
        )
        self.assertTrue(check_evidence(proof, "fixture", "source", "runtime", expected_plan=plan))
        proof["checks"][-1]["implementation_sha256"] = digest
        self.assertEqual(
            check_evidence(proof, "fixture", "source", "runtime", expected_plan=plan), []
        )
