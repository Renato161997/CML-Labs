import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "macsec", Path(__file__).resolve().parents[1] / "examples/security/macsec_probe.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def state():
    return {
        "own_mac": "02:00:00:35:00:02",
        "peer_mac": "02:00:00:35:00:01",
        "own_sci": int("0200003500020001", 16),
        "peer_sci": int("0200003500010001", 16),
        "sa0_floor": 10,
    }


def sa(an, pn=11):
    return {
        "an": an,
        "pn": pn,
        "active": True,
        "key": m.IDS[an],
        "InPktsOK": 5,
        "InPktsNotValid": 0,
    }


def status():
    return {
        "protect": True,
        "encrypt": True,
        "send_sci": True,
        "validate": "strict",
        "replay": True,
        "window": 0,
        "cipher_suite": "GCM-AES-128",
        "icv_length": 16,
        "offload": "off",
        "sci": "0x200003500020001",
        "encoding_sa": 0,
        "sa_list": [sa(0)],
        "rx_sc": [{"sci": "0x200003500010001", "active": True, "sa_list": [sa(0), sa(1)]}],
    }


def packet(an=0, secure_length=86):
    peer = bytes.fromhex("020000350001")
    own = bytes.fromhex("020000350002")
    sci = state()["peer_sci"]
    return (
        own
        + peer
        + b"\x88\xe5"
        + bytes([0x2C | an, secure_length if secure_length < 48 else 0])
        + (11).to_bytes(4, "big")
        + sci.to_bytes(8, "big")
        + bytes(secure_length)
        + bytes(16)
    )


class MACsec(unittest.TestCase):
    def test_repeat_configuration_never_reinitializes_security_associations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "macsec-state.json").write_text(json.dumps(state()))
            with (
                patch.object(m, "ROOT", root),
                patch.object(m, "status", return_value=status()),
                patch.object(m, "run") as commands,
            ):
                self.assertTrue(m.configure("RIGHT")["reused_without_sa_reset"])
                commands.assert_not_called()

    def test_unowned_existing_secy_is_rejected_before_network_changes(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(m, "ROOT", Path(directory)),
            patch.object(m, "run", return_value=SimpleNamespace(returncode=0)) as commands,
        ):
            with self.assertRaises(AssertionError):
                m.configure("LEFT")
            self.assertEqual(commands.call_count, 1)
            self.assertEqual(commands.call_args.args[0][:3], ["ip", "link", "show"])

    def test_actual_sci_an_packet_number_and_encrypted_header(self):
        for an in (0, 1):
            d = m.frame(packet(an))
            self.assertEqual(d["sci"], state()["peer_sci"])
            self.assertEqual(d["an"], an)
            self.assertEqual(d["pn"], 11)

    def test_short_secure_data_length_is_checked(self):
        self.assertEqual(m.frame(packet(0, 30))["length"], 74)
        bad = bytearray(packet(0, 30))
        bad[15] = 29
        with self.assertRaises(ValueError):
            m.frame(bad)

    def test_plaintext_and_truncated_frames_cannot_establish_macsec(self):
        self.assertIsNone(m.frame(bytes(50)))
        for bad in (packet()[:43], packet()[:45]):
            with self.assertRaises(ValueError):
                m.frame(bad)

    def test_authentication_only_missing_sci_and_version_bits_are_rejected(self):
        for flag in (0x20, 0x24, 0x28, 0x0C, 0xAC, 0x6C, 0x3C):
            bad = bytearray(packet())
            bad[14] = flag
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                m.frame(bad)

    def test_sci_source_port_and_nonzero_packet_number_must_agree(self):
        for start, end, replacement in [
            (6, 12, bytes(6)),
            (16, 20, bytes(4)),
            (26, 28, b"\x00\x02"),
        ]:
            bad = bytearray(packet())
            bad[start:end] = replacement
            with self.subTest(start=start), self.assertRaises(ValueError):
                m.frame(bad)

    def test_receive_channel_must_be_the_actual_selected_peer(self):
        m.verify(status(), state(), 0)
        bad = status()
        bad["rx_sc"][0]["sci"] = "0x12340001"
        with self.assertRaises(AssertionError):
            m.verify(bad, state(), 0)
        bad = status()
        bad["rx_sc"][0]["active"] = False
        with self.assertRaises(AssertionError):
            m.verify(bad, state(), 0)

    def test_disabled_encryption_or_validation_is_not_a_secure_baseline(self):
        for key, value in [
            ("encrypt", False),
            ("protect", False),
            ("validate", "check"),
            ("send_sci", False),
            ("replay", False),
            ("offload", "phy"),
            ("icv_length", 8),
        ]:
            bad = status()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                m.verify(bad, state(), 0)

    def test_packet_number_reset_is_rejected(self):
        bad = status()
        bad["sa_list"][0]["pn"] = 1
        with self.assertRaises(AssertionError):
            m.verify(bad, state(), 0)

    def test_inactive_or_duplicate_associations_do_not_count(self):
        for values in (
            [{**sa(0), "active": False}],
            [sa(0), sa(0)],
            [],
            [{**sa(0), "key": m.IDS[1]}],
        ):
            with self.assertRaises(AssertionError):
                m.association(values, 0)

    def test_zero_replies_are_not_confused_with_zero_loss(self):
        self.assertEqual(
            m.packet_counts("3 packets transmitted, 0 received, 100% packet loss"), (3, 0)
        )
        self.assertEqual(
            m.packet_counts("3 packets transmitted, 3 received, 0% packet loss"), (3, 3)
        )
        with self.assertRaises(AssertionError):
            m.packet_counts("no measurable probe output")

    def test_replay_window_and_encoding_must_be_exact(self):
        bad = status()
        bad["window"] = 32
        with self.assertRaises(AssertionError):
            m.verify(bad, state(), 0)
        with self.assertRaises(AssertionError):
            m.verify(status(), state(), 1)
        with self.assertRaises(AssertionError):
            m.verify(status(), state(), False)


if __name__ == "__main__":
    unittest.main()
