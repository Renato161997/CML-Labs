import importlib.util
import struct
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "dns_policy", Path(__file__).resolve().parents[1] / "examples" / "security" / "dns_policy.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
# Literal standard DNS question: ID 0x1234, one IN A, no flags/additional records.
GOOD = bytes.fromhex("12340000000100000000000007616c6c6f776564036c6162076578616d706c650000010001")
BAD = GOOD.replace(b"allowed", b"blocked")


class ClosedDNS(unittest.TestCase):
    def test_literal_question_and_case_normalization(self):
        self.assertEqual(m.question(GOOD), (0x1234, 0, m.GOOD, 1, 1))
        self.assertEqual(m.question(GOOD.replace(b"allowed", b"ALLOWED"))[2], m.GOOD)

    def test_actual_header_name_pointer_zero_ttl_and_fixed_a_bytes(self):
        response = m.answer(GOOD, "enforce")
        self.assertEqual(struct.unpack("!6H", response[:12]), (0x1234, 0x8000, 1, 1, 0, 0))
        self.assertEqual(response[12 : len(GOOD)], GOOD[12:])
        self.assertEqual(response[len(GOOD) :], bytes.fromhex("c00c00010001000000000004c6120001"))

    def test_block_bypass_and_unavailability_are_distinct_wire_outcomes(self):
        for mode, rcode, answers in [
            ("enforce", 3, 0),
            ("bypass", 0, 1),
            ("unavailable", 2, 0),
        ]:
            with self.subTest(mode=mode):
                response = m.answer(BAD, mode)
                header = struct.unpack("!6H", response[:12])
                self.assertEqual((header[1] & 15, header[3]), (rcode, answers))

    def test_unknown_name_is_refused_even_during_bypass(self):
        for mode in m.MODES:
            response = m.answer(GOOD.replace(b"allowed", b"outside"), mode)
            self.assertEqual(struct.unpack("!6H", response[:12])[1] & 15, 5)

    def test_unsupported_class_and_type_do_not_return_address(self):
        for tail in (struct.pack("!HH", 28, 1), struct.pack("!HH", 1, 3)):
            response = m.answer(GOOD[:-4] + tail, "enforce")
            self.assertEqual(struct.unpack("!6H", response[:12])[1] & 15, 4)
            self.assertEqual(len(response), len(GOOD))

    def test_compression_truncation_multiple_questions_edns_and_injected_flags_fail(
        self,
    ):
        cases = [
            GOOD[:12] + b"\xc0\x0c\x00\x01\x00\x01",
            GOOD[:-1],
            GOOD + b"\0",
            GOOD[:4] + b"\0\2" + GOOD[6:],
            GOOD[:10] + b"\0\1" + GOOD[12:],
            GOOD[:2] + b"\x80\0" + GOOD[4:],
            GOOD[:2] + b"\x08\0" + GOOD[4:],
            GOOD[:2] + b"\x00\x20" + GOOD[4:],
            GOOD[:12] + b"\x40" + GOOD[13:],
            GOOD[:13] + b"\xff" + GOOD[14:],
        ]
        for packet in cases:
            with self.subTest(packet=packet):
                response = m.answer(packet, "enforce")
                self.assertEqual(struct.unpack("!6H", response), (0x1234, 0x8001, 0, 0, 0, 0))

    def test_empty_or_oversize_message_cannot_amplify(self):
        for packet in (b"", b"\x12", GOOD.ljust(513, b"\0")):
            response = m.answer(packet, "enforce")
            self.assertEqual(len(response), 12)
            self.assertEqual(response[3] & 15, 1)

    def test_recursion_desired_is_echoed_but_never_advertised_available(self):
        response = m.answer(GOOD[:2] + b"\x01\0" + GOOD[4:], "enforce")
        self.assertEqual(struct.unpack("!H", response[2:4])[0], 0x8100)

    def test_tcp_read_assembles_partial_segments_and_rejects_early_close(self):
        sock = mock.Mock()
        sock.recv.side_effect = [b"a", b"bc"]
        self.assertEqual(m.read_exact(sock, 3), b"abc")
        sock.recv.side_effect = [b"a", b""]
        with self.assertRaises(ValueError):
            m.read_exact(sock, 3)

    def test_unknown_local_policy_fails_instead_of_allowing(self):
        with self.assertRaises(ValueError):
            m.answer(BAD, "anything")


if __name__ == "__main__":
    unittest.main()
