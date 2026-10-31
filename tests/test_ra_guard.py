import importlib.util
import struct
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "ra_guard", Path(__file__).resolve().parents[1] / "examples/security/ra_guard.py"
)
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)
MAC = bytes.fromhex("020000260001")


class RouterAdvertisementGuard(unittest.TestCase):
    def test_real_ipv6_pseudoheader_checksum_and_trusted_port(self):
        packet = ra.ra_frame(MAC, "fe80::1")
        allowed, info = ra.permitted(packet, "eth1", True)
        self.assertTrue(allowed)
        self.assertEqual(info, {"kind": "ra", "gateway": "fe80::1", "extension": False})
        self.assertFalse(ra.permitted(packet, "eth3", True)[0])

    def test_rogue_high_preference_requires_policy_withdrawal(self):
        packet = ra.ra_frame(MAC, "fe80::66", True)
        self.assertFalse(ra.permitted(packet, "eth3", True)[0])
        self.assertTrue(ra.permitted(packet, "eth3", False)[0])
        self.assertFalse(ra.permitted(packet, "eth1", True)[0])

    def test_hop_by_hop_header_cannot_hide_untrusted_ra(self):
        packet = ra.ra_frame(MAC, "fe80::66", True, True)
        allowed, info = ra.permitted(packet, "eth3", True)
        self.assertFalse(allowed)
        self.assertTrue(info["extension"])
        self.assertTrue(ra.permitted(packet, "eth3", False)[0])

    def test_bad_checksum_code_and_hop_limit_are_not_valid_ra(self):
        packet = ra.ra_frame(MAC, "fe80::1")
        for offset in (21, 55, 56, 68):
            bad = bytearray(packet)
            bad[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                ra.inspect(bad)

    def test_fragment_and_opaque_headers_fail_closed(self):
        for value in (44, 50, 51, 250):
            bad = bytearray(ra.ra_frame(MAC, "fe80::66"))
            bad[20] = value
            with self.subTest(next_header=value), self.assertRaises(ValueError):
                ra.permitted(bad, "eth3", True)

    def test_truncated_extension_chain_is_rejected(self):
        bad = bytearray(ra.ra_frame(MAC, "fe80::66", extension=True))
        bad[55] = 10
        with self.assertRaises(ValueError):
            ra.inspect(bad)
        with self.assertRaises(ValueError):
            ra.inspect(bad[:60])

    def test_invalid_option_is_rejected_even_with_correct_checksum(self):
        bad = bytearray(ra.ra_frame(MAC, "fe80::1"))
        bad[71] = 0
        bad[56:58] = bytes(2)
        pseudo = bytes(bad[22:54]) + struct.pack("!I3xB", len(bad) - 54, 58)
        bad[56:58] = struct.pack("!H", ra.checksum(pseudo + bytes(bad[54:])))
        with self.assertRaises(ValueError):
            ra.inspect(bad)

    def test_source_option_must_match_actual_frame_identity(self):
        bad = bytearray(ra.ra_frame(MAC, "fe80::1"))
        bad[6] ^= 4
        with self.assertRaises(ValueError):
            ra.inspect(bad)

    def test_other_lan_frames_still_forward(self):
        ipv4 = bytes(12) + b"\x08\x00" + bytes(40)
        self.assertEqual(ra.permitted(ipv4, "eth3", True), (True, {"kind": "other"}))
        echo = bytearray(ra.ra_frame(MAC, "fe80::1"))
        echo[54] = 128
        self.assertEqual(ra.permitted(echo, "eth3", True), (True, {"kind": "other"}))

    def test_tagged_frames_outside_declared_untagged_scope_are_rejected(self):
        packet = ra.ra_frame(MAC, "fe80::1")
        with self.assertRaises(ValueError):
            ra.inspect(packet[:12] + b"\x81\x00\x00\x0a" + packet[12:])

    def test_only_declared_advertisers_and_policy_states_are_accepted(self):
        for source in ("2001:db8::1", "fe80::99"):
            with self.assertRaises(ValueError):
                ra.ra_frame(MAC, source)
        with self.assertRaises(ValueError):
            ra.permitted(ra.ra_frame(MAC, "fe80::1"), "eth0", True)
        with self.assertRaises(ValueError):
            ra.permitted(ra.ra_frame(MAC, "fe80::1"), "eth3", 1)

    def test_invalid_ethernet_and_ipv6_lengths_do_not_pass(self):
        with self.assertRaises(ValueError):
            ra.inspect(bytes(5))
        packet = ra.ra_frame(MAC, "fe80::1")
        with self.assertRaises(ValueError):
            ra.inspect(packet[:53])
        with self.assertRaises(ValueError):
            ra.inspect(packet[:-1])
