"""Independent Ethernet/IPv4/TCP and PCAP witnesses; absence must fail closed."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/security"
if not SOURCE.exists():
    SOURCE = ROOT / "CML-Labs/examples/security"
sys.path.insert(0, str(SOURCE))
import packet_observer as observer

FRAME = bytes.fromhex(
    "020000000020 020000000010 0800 "
    "4500002d 0001 4000 40 06 0000 c612000a c6120014 "
    "c350 1f90 00000001 00000001 50 18 2000 0000 0000 474554202f"
)
PCAP = (
    bytes.fromhex(
        "d4c3b2a1 0200 0400 00000000 00000000 ffff0000 01000000 01000000 02000000 3b000000 3b000000"
    )
    + FRAME
)


class PacketObserverTests(unittest.TestCase):
    def test_independent_wire_frame_and_vlan_decode(self):
        for frame in (FRAME, FRAME[:12] + bytes.fromhex("8100000a0800") + FRAME[14:]):
            facts = observer.frame_facts(frame)
            self.assertEqual(facts["source"], "198.18.0.10")
            self.assertEqual(facts["destination"], "198.18.0.20")
            self.assertEqual(facts["source_port"], 50000)
            self.assertEqual(facts["destination_port"], 8080)
            self.assertEqual(facts["frame_sha256"], hashlib.sha256(frame).hexdigest())

    def test_fragmented_truncated_or_nonrequest_packets_are_not_evidence(self):
        fragment = bytearray(FRAME)
        fragment[20:22] = bytes.fromhex("2000")
        bad_ihl = bytearray(FRAME)
        bad_ihl[14] = 0x44
        bad_tcp = bytearray(FRAME)
        bad_tcp[46] = 0x10
        wrong_payload = FRAME[:-5] + b"OTHER"
        for frame in (
            b"",
            FRAME[:13],
            FRAME[:-1],
            bytes(fragment),
            bytes(bad_ihl),
            bytes(bad_tcp),
            wrong_payload,
        ):
            self.assertIsNone(observer.frame_facts(frame))

    def test_independent_pcap_and_corrupt_lengths(self):
        self.assertEqual(observer.pcap_frame(PCAP), FRAME)
        for data in (PCAP[:-1], PCAP + b"x", b"x" * 40, PCAP[:20]):
            with self.assertRaises(ValueError):
                observer.pcap_frame(data)

    def test_claimed_capture_requires_actual_matching_pcap(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            state = {
                "ready": True,
                "finished": True,
                "captured": True,
                "source": "198.18.0.10",
                "destination": "198.18.0.20",
                "destination_port": 8080,
                "frame_sha256": hashlib.sha256(FRAME).hexdigest(),
            }
            path = observer.state_path(folder, "p0")
            path.write_text(json.dumps(state))
            self.assertFalse(observer.verdict(folder, "p0")["observed"])
            (folder / "capture-p0.pcap").write_bytes(PCAP)
            self.assertTrue(observer.verdict(folder, "p0")["observed"])
            state["destination_port"] = 8081
            path.write_text(json.dumps(state))
            self.assertFalse(observer.verdict(folder, "p0")["observed"])

    def test_quiet_requires_ready_finished_and_full_window(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            valid = {
                "ready": True,
                "finished": True,
                "captured": False,
                "elapsed": 12.01,
                "window": 12,
            }
            for changes, expected in (
                ({}, True),
                ({"ready": False}, False),
                ({"finished": False}, False),
                ({"elapsed": 11.99}, False),
                ({"window": 0}, False),
                ({"captured": True}, False),
            ):
                observer.state_path(folder, "p0").write_text(json.dumps(dict(valid, **changes)))
                self.assertEqual(observer.verdict(folder, "p0")["quiet"], expected)

    def test_nonlinux_rejected_before_opening_raw_socket(self):
        with (
            patch.object(observer.sys, "platform", "win32"),
            patch.object(observer.socket, "socket") as raw,
        ):
            with self.assertRaises(RuntimeError):
                observer.listen(Path("unused"), "p0", 8080, "198.18.0.10", "198.18.0.20")
            raw.assert_not_called()


if __name__ == "__main__":
    unittest.main()
