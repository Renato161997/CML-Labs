import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "examples/wireless/radio_probe.py"
SPEC = importlib.util.spec_from_file_location("radio_probe", SOURCE)
radio = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(radio)

SETTINGS = {"role": "client", "auth": "wpa2", "ssid": "CML-SCOR014"}
WPA_STATUS = """bssid=aa:48:cd:00:00:00
freq=2437
ssid=CML-SCOR014
pairwise_cipher=CCMP
group_cipher=CCMP
key_mgmt=WPA2-PSK
wpa_state=COMPLETED
ip_address=198.18.50.2
"""
LINK = "Connected to aa:48:cd:00:00:00 (on wlan0)\n\tSSID: CML-SCOR014\n"


class RadioContract(unittest.TestCase):
    def test_status_and_kernel_association_must_agree(self):
        status = radio.parse_status(WPA_STATUS)
        self.assertTrue(all(radio.association(status, LINK, SETTINGS).values()))
        for field, value in [
            ("wpa_state", "4WAY_HANDSHAKE"),
            ("ssid", "OTHER"),
            ("key_mgmt", "NONE"),
            ("pairwise_cipher", "TKIP"),
            ("group_cipher", "TKIP"),
            ("bssid", "aa:00:00:00:00:01"),
        ]:
            with self.subTest(field=field):
                self.assertFalse(
                    all(radio.association({**status, field: value}, LINK, SETTINGS).values())
                )
        self.assertFalse(all(radio.association(status, "Not connected.\n", SETTINGS).values()))

    def test_open_and_psk_have_distinct_protocol_requirements(self):
        value = {**SETTINGS, "auth": "open"}
        status = {**radio.parse_status(WPA_STATUS), "key_mgmt": "NONE", "pairwise_cipher": "NONE"}
        self.assertTrue(all(radio.association(status, LINK, value).values()))
        self.assertFalse(all(radio.association(status, LINK, SETTINGS).values()))

    def test_ping_counts_do_not_confuse_zero_and_total_loss(self):
        self.assertEqual(
            radio.packet_counts("3 packets transmitted, 3 received, 0% packet loss"), (3, 3)
        )
        self.assertEqual(
            radio.packet_counts("3 packets transmitted, 0 received, 100% packet loss"), (3, 0)
        )
        with self.assertRaises(ValueError):
            radio.packet_counts("ping: bind: No such device")

    def test_duplicate_status_fields_are_ambiguous(self):
        with self.assertRaises(ValueError):
            radio.parse_status("wpa_state=SCANNING\nwpa_state=COMPLETED")

    def test_fixture_schema_rejects_injected_or_unbounded_ssids(self):
        for value in [
            {**SETTINGS, "ssid": 'CML-X"\npsk="injected'},
            {**SETTINGS, "ssid": "CML-" + "A" * 30},
            {**SETTINGS, "role": "host"},
            {**SETTINGS, "auth": "auto"},
            {**SETTINGS, "target": "10.0.0.1"},
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                radio.settings(value)

    def test_wrong_key_and_wrong_ssid_are_separate_faults(self):
        healthy = radio.configuration(SETTINGS)
        bad_key = radio.configuration(SETTINGS, "key")
        bad_ssid = radio.configuration(SETTINGS, "ssid")
        self.assertIn('ssid="CML-SCOR014"', bad_key)
        self.assertNotIn(radio.KEY, bad_key)
        self.assertIn(radio.KEY, bad_ssid)
        self.assertIn('ssid="CML-SCOR014-ABSENT"', bad_ssid)
        self.assertIn("proto=RSN", healthy)
        self.assertIn("pairwise=CCMP", healthy)
        with self.assertRaises(ValueError):
            radio.configuration({**SETTINGS, "auth": "open"}, "key")
        with self.assertRaises(ValueError):
            radio.configuration({**SETTINGS, "role": "ap"}, "ssid")

    def test_process_signal_is_refused_for_a_different_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            proc = root / "proc"
            (proc / "99").mkdir(parents=True)
            (proc / "99/cmdline").write_bytes(b"/usr/sbin/wpa_supplicant\0-c/other.conf\0")
            (root / "w.pid").write_text("99")
            with patch.object(radio, "ROOT", root), patch.object(radio, "PROC", proc):
                with patch.object(radio.os, "kill") as kill, self.assertRaises(RuntimeError):
                    radio.stop("client")
                kill.assert_not_called()
                self.assertTrue((root / "w.pid").exists())

    def test_owned_process_requires_exact_executable_and_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            proc = root / "proc"
            (proc / "99").mkdir(parents=True)
            command = proc / "99/cmdline"
            with patch.object(radio, "ROOT", root), patch.object(radio, "PROC", proc):
                config = str(root / "w.conf").encode()
                command.write_bytes(b"/usr/sbin/wpa_supplicant\0-c" + config + b"\0-iwlan0\0")
                self.assertTrue(radio.owned_process("client", 99))
                command.write_bytes(b"/usr/sbin/other\0-c" + config + b"\0")
                self.assertFalse(radio.owned_process("client", 99))
                for pid in [0, 1, -1, True]:
                    with self.subTest(pid=pid), self.assertRaises(ValueError):
                        radio.owned_process("client", pid)

    def test_incomplete_handshake_can_associate_without_authorized_data(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(radio, "ROOT", Path(folder)):
            radio.paths("client")[0].write_text(radio.configuration(SETTINGS, "key"))
            with (
                patch.object(radio, "interface_ready"),
                patch.object(
                    radio, "snapshot", return_value=({"wpa_state": "4WAY_HANDSHAKE"}, LINK)
                ),
                patch.object(radio.time, "monotonic", side_effect=[0, 0, 13]),
                patch.object(radio.time, "sleep"),
                patch.object(
                    radio,
                    "run_command",
                    return_value=SimpleNamespace(
                        stdout="3 packets transmitted, 0 received", returncode=1
                    ),
                ),
            ):
                self.assertEqual(radio.check(SETTINGS, "key", "down")["received"], 0)

    def test_any_completed_authentication_fails_the_negative_window(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(radio, "ROOT", Path(folder)):
            radio.paths("client")[0].write_text(radio.configuration(SETTINGS, "key"))
            with (
                patch.object(radio, "interface_ready"),
                patch.object(
                    radio, "snapshot", return_value=(radio.parse_status(WPA_STATUS), LINK)
                ),
                patch.object(radio, "run_command") as packet,
                self.assertRaises(AssertionError),
            ):
                radio.check(SETTINGS, "key", "down")
            packet.assert_not_called()

    def test_completed_authentication_without_packets_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(radio, "ROOT", Path(folder)):
            radio.paths("client")[0].write_text(radio.configuration(SETTINGS))
            with (
                patch.object(radio, "interface_ready"),
                patch.object(
                    radio, "snapshot", return_value=(radio.parse_status(WPA_STATUS), LINK)
                ),
                patch.object(radio.time, "monotonic", side_effect=[0, 0, 46]),
                patch.object(radio.time, "sleep"),
                patch.object(
                    radio,
                    "run_command",
                    return_value=SimpleNamespace(
                        stdout="3 packets transmitted, 0 received", returncode=1
                    ),
                ),
                self.assertRaises(TimeoutError),
            ):
                radio.check(SETTINGS, "none", "up")


if __name__ == "__main__":
    unittest.main()
