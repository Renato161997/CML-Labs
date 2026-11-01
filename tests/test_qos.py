import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "qos_probe", Path(__file__).resolve().parents[1] / "examples/security/qos_probe.py"
)
qos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qos)
NONCE = "a" * 24


class QoSWireObservations(unittest.TestCase):
    def measured(self, data=16, tos=184):
        state = qos.Observations()
        state.reset(NONCE)
        for seq in range(data):
            state.receive(qos.packet(NONCE, "data", seq), "data", tos)
        for seq in range(4):
            state.receive(qos.packet(NONCE, "control", seq), "control", 0)
        return state

    def test_fixed_size_payload_and_exact_sequence(self):
        for kind, count in qos.LIMITS.items():
            for seq in range(count):
                data = qos.packet(NONCE, kind, seq)
                self.assertEqual(len(data), qos.SIZES[kind])
                self.assertEqual(
                    qos.decode(data, kind), {"nonce": NONCE, "kind": kind, "sequence": seq}
                )

    def test_invalid_payload_contracts_are_rejected(self):
        base = {"nonce": NONCE, "kind": "data", "sequence": 0}
        for key, value in [
            ("nonce", "old"),
            ("sequence", True),
            ("sequence", 16),
            ("sequence", -1),
            ("kind", "control"),
            ("extra", "x"),
        ]:
            data = {**base, key: value}
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                qos.decode(json.dumps(data).encode().ljust(1000, b" "), "data")
        for raw in [b"", b"x" * 1000, b"null".ljust(1000, b" "), qos.packet(NONCE, "data", 0)[:-1]]:
            with self.subTest(raw_length=len(raw)), self.assertRaises(ValueError):
                qos.decode(raw, "data")

    def test_wrong_port_class_is_rejected(self):
        with self.assertRaises(ValueError):
            qos.decode(qos.packet(NONCE, "data", 0), "control")

    def test_actual_marking_required_and_ecn_cannot_substitute(self):
        self.assertTrue(qos.accepted(self.measured().snapshot(NONCE), "marked"))
        for tos in [0, 46, 185, 188]:
            self.assertFalse(qos.accepted(self.measured(tos=tos).snapshot(NONCE), "marked"))
        self.assertTrue(qos.accepted(self.measured(tos=0).snapshot(NONCE), "unmarked"))

    def test_limited_requires_some_data_but_not_all(self):
        for count in [1, 7, 15]:
            self.assertTrue(qos.accepted(self.measured(data=count).snapshot(NONCE), "limited"))
        for count in [0, 16]:
            self.assertFalse(qos.accepted(self.measured(data=count).snapshot(NONCE), "limited"))

    def test_control_traffic_remains_independent(self):
        state = self.measured(data=1)
        state.receive(qos.packet(NONCE, "control", 0), "control", 184)
        self.assertFalse(qos.accepted(state.snapshot(NONCE), "limited"))
        data = self.measured(data=1).snapshot(NONCE)
        data["sequences"]["control"].pop()
        self.assertFalse(qos.accepted(data, "limited"))

    def test_duplicates_and_malformed_packets_fail_the_window(self):
        state = self.measured()
        state.receive(qos.packet(NONCE, "data", 0), "data", 184)
        self.assertFalse(qos.accepted(state.snapshot(NONCE), "marked"))
        state = self.measured()
        state.receive(b"bad", "data", 184)
        self.assertFalse(qos.accepted(state.snapshot(NONCE), "marked"))

    def test_stale_generation_cannot_supply_fresh_evidence(self):
        state = self.measured()
        fresh = "b" * 24
        state.reset(fresh)
        state.receive(qos.packet(NONCE, "data", 0), "data", 184)
        data = state.snapshot(fresh)
        self.assertEqual(data["sequences"], {"data": [], "control": []})
        with self.assertRaises(ValueError):
            state.snapshot(NONCE)

    def test_missing_ancillary_tos_is_not_guessed(self):
        state = self.measured()
        state.receive(qos.packet(NONCE, "data", 0), "data", None)
        self.assertEqual(state.snapshot(NONCE)["malformed"], 1)
        self.assertFalse(qos.accepted(state.snapshot(NONCE), "marked"))

    def test_unknown_observation_mode_is_refused(self):
        self.assertFalse(qos.accepted(self.measured().snapshot(NONCE), "configuration-only"))


if __name__ == "__main__":
    unittest.main()
