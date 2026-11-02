import importlib.util
import struct
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "first_hop_wire",
    Path(__file__).resolve().parents[1] / "examples" / "security" / "first_hop_wire.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SERVER_MAC = bytes.fromhex("020000000020")


class WireProfile(unittest.TestCase):
    def frame(self, message=1, **kwargs):
        return m.make_dhcp(
            message,
            0x12345678,
            SERVER_MAC if message in (2, 5) else m.CLIENT_MAC,
            **kwargs,
        )

    def ip_edit(self, frame, start, value):
        raw = bytearray(frame)
        raw[14 + start : 14 + start + len(value)] = value
        raw[24:26] = b"\0\0"
        raw[24:26] = struct.pack("!H", m.checksum(bytes(raw[14:34])))
        return bytes(raw)

    def test_known_ones_complement_checksum_vector(self):
        self.assertEqual(m.checksum(bytes.fromhex("0001f203f4f5f6f7")), 0x220D)

    def test_bootp_wire_offsets_and_cookie_are_explicit(self):
        frame = self.frame()
        boot = frame[42:]
        self.assertEqual(m.BOOT.size, 236)
        self.assertEqual(boot[:8], bytes.fromhex("0101060012345678"))
        self.assertEqual(boot[10:12], bytes.fromhex("8000"))
        self.assertEqual(boot[28:34], m.CLIENT_MAC)
        self.assertEqual(boot[236:240], bytes.fromhex("63825363"))
        self.assertEqual(boot[240:244], bytes.fromhex("350101ff"))

    def test_each_dora_message_preserves_real_transaction_and_roles(self):
        for kind in (1, 2, 3, 5):
            with self.subTest(kind=kind):
                frame = self.frame(kind)
                value = m.dhcp(frame)
                self.assertEqual(value["message"], kind)
                self.assertEqual(value["xid"], 0x12345678)
                self.assertEqual(value["client_mac"], m.CLIENT_MAC)
                self.assertEqual(value["lease"], 600 if kind in (2, 5) else None)
                self.assertEqual(value["offered"], m.LEASED if kind in (2, 5) else "0.0.0.0")

    def test_short_real_lease_option_is_encoded_in_network_byte_order(self):
        frame = self.frame(5, lease=3)
        self.assertIn(bytes.fromhex("330400000003"), frame)
        self.assertEqual(m.dhcp(frame)["lease"], 3)

    def test_invalid_ipv4_checksum_cannot_be_parsed_as_dhcp(self):
        raw = bytearray(self.frame())
        raw[22] ^= 1
        with self.assertRaises(ValueError):
            m.dhcp(bytes(raw))

    def test_fragments_and_reserved_flag_are_rejected_with_valid_header_checksum(self):
        for flags in (0x2000, 1, 0x8000):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                m.dhcp(self.ip_edit(self.frame(), 6, struct.pack("!H", flags)))

    def test_unicast_destination_cannot_bypass_selecting_profile(self):
        with self.assertRaises(ValueError):
            m.dhcp(self.ip_edit(self.frame(), 16, m.ip_bytes(m.SERVER)))

    def test_malformed_udp_length_or_nonzero_checksum_fails(self):
        for offset, value in ((38, b"\x00\x08"), (40, b"\x00\x01")):
            raw = bytearray(self.frame())
            raw[offset : offset + 2] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                m.dhcp(bytes(raw))

    def test_missing_cookie_or_invalid_bootp_role_fails(self):
        for offset, value in ((42, b"\x02"), (42 + 236, b"\x00"), (42 + 3, b"\x01")):
            raw = bytearray(self.frame())
            raw[offset : offset + len(value)] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                m.dhcp(bytes(raw))

    def test_option_duplicates_overload_and_truncation_are_not_merged(self):
        for data in (
            b"\x35\x01\x01\x35\x01\x03\xff",
            b"\x34\x01\x01\xff",
            b"\x35\x04\x01",
            b"\x35",
            b"\x35\x01\x01",
            b"\xff\x01",
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                m.options(data)

    def test_dhcp_ethernet_padding_is_not_confused_with_udp_payload(self):
        self.assertEqual(m.dhcp(self.frame() + b"\0" * 20)["message"], 1)

    def test_tagged_and_ip_option_profiles_are_explicitly_unsupported(self):
        raw = bytearray(self.frame())
        raw[12:14] = b"\x81\x00"
        with self.assertRaises(ValueError):
            m.dhcp(bytes(raw))
        with self.assertRaises(ValueError):
            m.dhcp(self.ip_edit(self.frame(), 0, b"\x46"))

    def test_unbounded_or_noninteger_constructor_values_fail(self):
        for xid in (-1, 2**32, True):
            with self.subTest(xid=xid), self.assertRaises(ValueError):
                m.make_dhcp(1, xid, m.CLIENT_MAC)
        for lease in (0, 3601, True):
            with self.subTest(lease=lease), self.assertRaises(ValueError):
                self.frame(5, lease=lease)

    def test_pcap_uses_ethernet_link_type_and_exact_capture_lengths(self):
        frame = self.frame()
        data = m.pcap([frame])
        self.assertEqual(data[:4], bytes.fromhex("d4c3b2a1"))
        self.assertEqual(struct.unpack("<I", data[20:24])[0], 1)
        self.assertEqual(struct.unpack("<IIII", data[24:40]), (1, 0, len(frame), len(frame)))
        self.assertEqual(data[40:], frame)


if __name__ == "__main__":
    unittest.main()
