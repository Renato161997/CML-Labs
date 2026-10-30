"""Validate received DSCP proof against independent wire bytes and phase controls."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/security"
if not SOURCE.exists():
    SOURCE = ROOT / "CML-Labs/examples/security"
sys.path.insert(0, str(SOURCE))

import netflow_fixture
import qos_observer

GOLDEN = bytes.fromhex(
    "0005 0001 000003e8 6553f100 00000000 00000007 00 00 0000 "
    "c6120a0a c6121414 00000000 0001 0002 00000003 0000012c "
    "00000064 000000c8 d431 1f90 00 10 06 00 0000 0000 18 18 0000"
)


class QosObserverTests(unittest.TestCase):
    def test_registered_guest_profile_can_run_observer_cli(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from embed_webhook import NATIVE_PROFILES

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for guest, source in NATIVE_PROFILES["native-qos-flow"]["OUTSIDE"].items():
                shutil.copyfile(ROOT / source, folder / Path(guest).name)
            state = folder / "state.json"
            state.write_text(json.dumps({"records": netflow_fixture.parse_v5(GOLDEN)}))
            result = subprocess.run(
                [sys.executable, str(folder / "q.py"), "8080", "0", "--state", str(state)],
                cwd=folder,
                check=False,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["observed"])

    def test_actual_wire_tos_preserves_ecn_separation(self):
        for ecn in range(4):
            wire = bytearray(GOLDEN)
            wire[63] = 26 * 4 + ecn
            state = {"records": netflow_fixture.parse_v5(bytes(wire))}
            self.assertTrue(qos_observer.proof(state, 8080, 26)["observed"])
            self.assertFalse(qos_observer.proof(state, 8080, 0)["observed"])

    def test_missing_mixed_or_stale_phase_evidence_fails_closed(self):
        unmarked = netflow_fixture.parse_v5(GOLDEN)[0]
        marked = dict(unmarked, tos=104)
        for records in ([], [unmarked], [marked, unmarked]):
            self.assertFalse(qos_observer.proof({"records": records}, 8080, 26)["observed"])
        self.assertFalse(qos_observer.proof({"records": [marked]}, 8081, 26)["observed"])
        self.assertTrue(qos_observer.proof({"records": [unmarked]}, 8080, 0)["observed"])

    def test_wrong_tuple_protocol_or_empty_counters_are_not_packet_proof(self):
        record = netflow_fixture.parse_v5(GOLDEN)[0]
        for changes in (
            {"source": "198.18.10.11"},
            {"destination": "198.18.20.21"},
            {"protocol": 17},
            {"packets": 0},
            {"bytes": 0},
        ):
            state = {"records": [dict(record, **changes)]}
            self.assertFalse(qos_observer.proof(state, 8080, 0)["observed"])
        for invalid in (-1, 64, True, "26"):
            with self.assertRaises(ValueError):
                qos_observer.proof({"records": [record]}, 8080, invalid)


if __name__ == "__main__":
    unittest.main()
