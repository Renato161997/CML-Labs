"""Independent golden wire format and real UDP tests for the teaching collector."""

import importlib.util
import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "netflow_fixture", ROOT / "examples/security/netflow_fixture.py"
)
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)

# Independent 24-byte header and 48-byte record, using Cisco tables B-3/B-4.
GOLDEN = bytes.fromhex(
    "0005 0001 000003e8 6553f100 00000000 00000007 00 00 0000 "
    "c6120a0a c6121414 00000000 0001 0002 00000003 0000012c "
    "00000064 000000c8 d431 1f90 00 10 06 00 0000 0000 18 18 0000"
)


class NetflowFixtureTests(unittest.TestCase):
    def test_independent_golden_record_offsets_and_byte_order(self):
        self.assertEqual(
            fixture.parse_v5(GOLDEN),
            [
                {
                    "source": "198.18.10.10",
                    "destination": "198.18.20.20",
                    "packets": 3,
                    "bytes": 300,
                    "source_port": 54321,
                    "destination_port": 8080,
                    "protocol": 6,
                    "tos": 0,
                    "sequence": 7,
                }
            ],
        )

    def test_invalid_binary_datagrams_are_rejected(self):
        invalid = (
            b"not a NetFlow packet",
            GOLDEN[:-1],
            GOLDEN + b"unexpected trailing bytes",
            b"\x00\x09" + GOLDEN[2:],
            GOLDEN[:2] + b"\x00\x02" + GOLDEN[4:],
            GOLDEN[:2] + b"\x00\x00" + GOLDEN[4:],
            GOLDEN[:12] + b"\x3b\x9a\xca\x00" + GOLDEN[16:],
        )
        for value in invalid:
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                fixture.parse_v5(value)

    def receive_one(self, expected_exporter):
        with tempfile.TemporaryDirectory(prefix="owned-cml-flow-tests-") as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            path = root / "flows.json"
            collector = fixture.Collector("127.0.0.1", 0, expected_exporter, path)
            thread = threading.Thread(target=collector.run, daemon=True)
            thread.start()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                    sender.sendto(GOLDEN, collector.socket.getsockname())
                until = time.monotonic() + 2
                while time.monotonic() < until:
                    value = fixture.snapshot(path)
                    if value["datagrams"] + value["rejected"]:
                        return value
                    time.sleep(0.01)
                self.fail("Local UDP fixture was not consumed")
            finally:
                collector.close()
                thread.join(timeout=2)
                collector.socket.close()

    def test_actual_udp_collection_preserves_the_wire_observation(self):
        value = self.receive_one("127.0.0.1")
        self.assertEqual(value["datagrams"], 1)
        self.assertEqual(value["rejected"], 0)
        self.assertEqual(value["records"], fixture.parse_v5(GOLDEN))

    def test_unexpected_udp_exporter_cannot_populate_flow_state(self):
        value = self.receive_one("127.0.0.2")
        self.assertEqual(value["datagrams"], 0)
        self.assertEqual(value["rejected"], 1)
        self.assertEqual(value["records"], [])

    def test_old_port_observation_cannot_satisfy_a_fresh_phase(self):
        with tempfile.TemporaryDirectory(prefix="owned-cml-flow-tests-") as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            path = root / "flows.json"
            fixture.save(path, {"datagrams": 1, "rejected": 0, "records": fixture.parse_v5(GOLDEN)})
            self.assertTrue(fixture.proof(path, 8080)["observed"])
            self.assertFalse(fixture.proof(path, 8081)["observed"])
            self.assertFalse(fixture.quiet(path, 8080, 0.02)["quiet"])
            self.assertTrue(fixture.quiet(path, 8081, 0.02)["quiet"])

    def test_analysis_suppression_does_not_erase_observed_raw_ports(self):
        with tempfile.TemporaryDirectory(prefix="owned-cml-flow-tests-") as directory:
            root = Path(directory).resolve()
            self.assertTrue(root.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            path = root / "flows.json"
            base = fixture.parse_v5(GOLDEN)[0]
            records = [{**base, "destination_port": p} for p in range(10000, 10007)]
            fixture.save(path, {"datagrams": 1, "rejected": 0, "records": records})
            before = json.loads(path.read_text())
            self.assertTrue(fixture.analyze(path)["flagged"])
            suppressed = fixture.analyze(path, suppress_scan=True)
            self.assertFalse(suppressed["flagged"])
            self.assertEqual(suppressed["distinct_ports"], 7)
            self.assertEqual(json.loads(path.read_text()), before)


if __name__ == "__main__":
    unittest.main()
