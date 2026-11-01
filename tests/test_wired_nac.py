"""Peer trust, fixed configurations, kernel-state and process guard tests."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography import x509
from cryptography.hazmat.primitives import serialization

spec = importlib.util.spec_from_file_location(
    "wired_nac", Path(__file__).resolve().parents[1] / "examples/security/wired_nac.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PeerCertificateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = mock.patch.object(m, "ROOT", self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_generated_peer_certificate_matches_private_key_and_expected_identity(self):
        m.certificates("AUTH")
        raw = (self.root / "identity.pem").read_bytes()
        cert = m.accept_certificate(raw, "AUTH")
        key = serialization.load_pem_private_key((self.root / "identity.key").read_bytes(), None)
        self.assertEqual(cert.public_key().public_numbers(), key.public_key().public_numbers())
        self.assertTrue(cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        self.assertGreaterEqual(cert.public_key().key_size, 2048)
        with self.assertRaises(ValueError):
            m.accept_certificate(raw, "CLIENT")

    def test_fresh_configurations_create_distinct_private_material(self):
        m.certificates("CLIENT")
        first = (self.root / "identity.pem").read_bytes()
        m.certificates("CLIENT")
        second = (self.root / "identity.pem").read_bytes()
        self.assertNotEqual(first, second)
        m.accept_certificate(second, "CLIENT")

    def test_invalid_certificate_and_fixture_links_refused(self):
        with self.assertRaises(ValueError):
            m.accept_certificate(b"not a certificate", "AUTH")
        with (
            mock.patch.object(Path, "is_symlink", return_value=True),
            self.assertRaises(ValueError),
        ):
            m.write(self.root / "anything", "data")


class ConfigurationTests(unittest.TestCase):
    def test_wired_supplicant_requires_eap_tls_ca_and_exact_server_name(self):
        good = m.supplicant_config()
        bad = m.supplicant_config(True)
        for text in (good, bad):
            self.assertIn("ap_scan=0", text)
            self.assertIn("key_mgmt=IEEE8021X", text)
            self.assertIn("eap=TLS", text)
            self.assertIn('ca_cert="/lab/peer.pem"', text)
            self.assertIn('private_key="/lab/identity.key"', text)
            self.assertIn('phase1="allow_canned_success=0"', text)
            self.assertNotIn("\n allow_canned_success=", text)
            self.assertIn("eapol_flags=0", text)
        self.assertIn('domain_match="auth.cml-lab.example"', good)
        self.assertEqual(good.replace("auth.cml-lab.example", "wrong.cml-lab.example"), bad)

    def test_authenticator_uses_wired_eap_server_and_peer_ca(self):
        text = m.hostapd_config()
        for line in (
            "driver=wired",
            "interface=eth1",
            "ieee8021x=1",
            "use_pae_group_addr=1",
            "eap_server=1",
            "ca_cert=/lab/peer.pem",
            "private_key=/lab/identity.key",
        ):
            self.assertIn(line + "\n", text)
        self.assertNotIn("wpa_passphrase", text)


class KernelAndStatusTests(unittest.TestCase):
    def result(self, stdout, code=0):
        return subprocess.CompletedProcess([], code, stdout, "")

    def test_authentication_requires_actual_authorized_station_flag(self):
        for text, expected in (
            ("flags=[AUTH][ASSOC][AUTHORIZED]\n", True),
            ("flags=[AUTH][ASSOC]\n", False),
            ("FAIL\n", False),
            ("notflags=[AUTHORIZED]\n", False),
        ):
            with (
                self.subTest(text=text),
                mock.patch.object(m, "run", return_value=self.result(text)),
            ):
                self.assertEqual(m.authenticated(), expected)

    def test_control_route_must_be_an_actual_unreachable_for_exact_data_prefix(self):
        for rows, expected in (
            ([], False),
            ([{"type": "unicast", "dst": "198.18.10.0/24"}], False),
            ([{"type": "unreachable", "dst": "198.18.99.0/30"}], False),
            ([{"type": "unreachable", "dst": "198.18.10.0/24"}], True),
        ):
            with (
                self.subTest(rows=rows),
                mock.patch.object(m, "run", return_value=self.result(json.dumps(rows))),
            ):
                self.assertEqual(m.control_isolated(), expected)

    def test_locked_and_disabled_learning_must_both_be_observed(self):
        for data, expected in (
            ([{"locked": True, "learning": False}], True),
            ([{"locked": False, "learning": False}], False),
            ([{"locked": True, "learning": True}], False),
            ([], False),
        ):
            with (
                self.subTest(data=data),
                mock.patch.object(m, "run", return_value=self.result(json.dumps(data))),
            ):
                self.assertEqual(m.locked(), expected)

    def test_only_unlocked_fixed_mac_on_exact_port_is_admitted(self):
        for row, expected in (
            ({"mac": m.MAC, "ifname": "eth1", "flags": ["master"]}, True),
            ({"mac": m.MAC, "dev": "eth2"}, False),
            ({"mac": "02:00:00:00:00:66", "dev": "eth1"}, False),
            ({"mac": m.MAC, "dev": "eth1", "locked": True}, False),
            ({"mac": m.MAC, "dev": "eth1", "flags": ["locked"]}, False),
        ):
            with (
                self.subTest(row=row),
                mock.patch.object(m, "run", return_value=self.result(json.dumps([row]))),
            ):
                self.assertEqual(m.admitted(), expected)

    def test_supplicant_requires_completed_transport_and_eap_success(self):
        for text, expected in (
            ("wpa_state=COMPLETED\nEAP state=SUCCESS\n", True),
            ("wpa_state=COMPLETED\nEAP state=FAILURE\n", False),
            ("wpa_state=ASSOCIATED\nEAP state=SUCCESS\n", False),
        ):
            with (
                self.subTest(text=text),
                mock.patch.object(m, "run", return_value=self.result(text)),
            ):
                self.assertEqual(m.client_status(), expected)

    def test_incomplete_packet_output_is_not_a_blocked_verdict(self):
        with (
            mock.patch.object(m, "run", return_value=self.result("command failed")),
            self.assertRaises(ValueError),
        ):
            m.packets()
        for count in range(4):
            with mock.patch.object(
                m, "run", return_value=self.result(f"3 packets transmitted, {count} received\n")
            ):
                self.assertEqual(m.packets(), count)


class RecoveryGuardTests(unittest.TestCase):
    def test_control_probe_removes_only_its_route_even_when_observation_fails(self):
        with (
            mock.patch.object(m, "client_status", return_value=True),
            mock.patch.object(m, "peer_certificate"),
            mock.patch.object(m, "run") as command,
            mock.patch.object(m, "packets", side_effect=ValueError("incomplete")),
            self.assertRaises(ValueError),
        ):
            m.control_no_bypass()
        self.assertEqual(
            command.call_args_list[-1].args[0],
            ["ip", "route", "del", "198.18.10.20/32", "via", "198.18.99.1", "dev", "eth2"],
        )

    def test_control_probe_requires_blocked_alternative_and_recovered_data(self):
        with (
            mock.patch.object(m, "client_status", return_value=True),
            mock.patch.object(m, "peer_certificate"),
            mock.patch.object(m, "run"),
            mock.patch.object(m, "packets", side_effect=[0, 3, 3]) as packets,
        ):
            result = m.control_no_bypass()
            self.assertTrue(result["actual_management_path_blocked"])
            self.assertTrue(result["normal_data_recovered"])
            self.assertEqual(result["consecutive_recovery_samples"], 2)
            self.assertEqual(packets.call_args_list[0].kwargs, {"source": True})

    def test_recovery_requires_two_complete_consecutive_trains(self):
        with (
            mock.patch.object(m, "packets", side_effect=[2, 3, 0, 3, 3]) as packets,
            mock.patch.object(m.time, "monotonic", return_value=0),
            mock.patch.object(m.time, "sleep"),
        ):
            m.recovered_data()
        self.assertEqual(packets.call_count, 5)

    def test_recovery_rejects_even_complete_samples_after_its_deadline(self):
        with (
            mock.patch.object(m, "packets", return_value=3),
            mock.patch.object(m.time, "monotonic", side_effect=[0, 16]),
            self.assertRaises(AssertionError),
        ):
            m.recovered_data()

    def test_pid_guard_rechecks_an_empty_identity_until_the_process_exits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            proc = root / "proc"
            (proc / "99").mkdir(parents=True)
            (root / "gate.pid").write_text("99")
            state = proc / "99" / "stat"
            state.write_text("99 (python3) S 1 2")

            def exiting(_):
                state.write_text("99 (python3) Z 1 2")
                return b""

            with (
                mock.patch.object(m, "ROOT", root),
                mock.patch.object(m, "PROC", proc),
                mock.patch.object(m, "PID_OWNER_UID", root.stat().st_uid),
                mock.patch.object(Path, "read_bytes", exiting),
                mock.patch.object(m.time, "sleep"),
            ):
                self.assertIsNone(m.owned_pid("gate"))

    def test_pid_guard_never_accepts_a_live_process_with_empty_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            proc = root / "proc"
            (proc / "99").mkdir(parents=True)
            (root / "gate.pid").write_text("99")
            (proc / "99" / "stat").write_text("99 (python3) S 1 2")
            (proc / "99" / "cmdline").write_bytes(b"")
            with (
                mock.patch.object(m, "ROOT", root),
                mock.patch.object(m, "PROC", proc),
                mock.patch.object(m, "PID_OWNER_UID", root.stat().st_uid),
                mock.patch.object(m.time, "sleep") as sleep,
                self.assertRaises(ValueError),
            ):
                m.owned_pid("gate")
            self.assertEqual(sleep.call_count, 3)

    def test_pid_guard_accepts_only_owned_identity_and_handles_exited_process(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            proc = root / "proc"
            (proc / "99").mkdir(parents=True)
            (root / "gate.pid").write_text("99")
            (proc / "99" / "stat").write_text("99 (python3) S 1 2")
            with (
                mock.patch.object(m, "ROOT", root),
                mock.patch.object(m, "PROC", proc),
                mock.patch.object(m, "PID_OWNER_UID", root.stat().st_uid),
            ):
                (proc / "99" / "cmdline").write_bytes(b"/usr/bin/python3\0/lab/n.py\0gate\0")
                self.assertEqual(m.owned_pid("gate"), 99)
                (proc / "99" / "cmdline").write_bytes(b"/usr/bin/python3\0/some/other.py\0gate\0")
                with self.assertRaises(AssertionError):
                    m.owned_pid("gate")
                (proc / "99" / "stat").write_text("99 (python3) Z 1 2")
                self.assertIsNone(m.owned_pid("gate"))


if __name__ == "__main__":
    unittest.main()
