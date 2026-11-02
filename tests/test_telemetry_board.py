import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples" / "management"))
spec = importlib.util.spec_from_file_location(
    "telemetry_board",
    Path(__file__).resolve().parents[1] / "examples" / "management" / "telemetry_board.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TypedTelemetry(unittest.TestCase):
    OID = ".1.3.6.1.2.1.2.2.1.10.2"

    def sample(self, **changes):
        return {
            "agent": "R1",
            "interface": "Ethernet0/1",
            "index": 2,
            "uptime_ticks": 10000,
            "monotonic": 10.0,
            "state": 1,
            "rx_bytes": 100,
            "tx_bytes": 200,
            **changes,
        }

    def test_exact_oid_and_counter_type_are_required(self):
        self.assertEqual(m.value_of(self.OID, self.OID + " = Counter32: 123", "counter"), 123)
        for text in (
            self.OID + " = INTEGER: 123",
            ".1.2.3 = Counter32: 123",
            self.OID + " = No Such Object",
            self.OID + " = Counter32: -1",
            self.OID + " = Counter32: 4294967296",
            "x" * 2049,
        ):
            with self.subTest(text=text[:80]), self.assertRaises(m.Unavailable):
                m.value_of(self.OID, text, "counter")

    def test_operational_down_is_a_real_enumerated_value(self):
        for text, value in (("up(1)", 1), ("down(2)", 2), ("7", 7)):
            self.assertEqual(m.value_of(self.OID, self.OID + " = INTEGER: " + text, "state"), value)
        with self.assertRaises(m.Unavailable):
            m.value_of(self.OID, self.OID + " = INTEGER: 0", "state")

    def test_rates_are_bytes_per_elapsed_second_not_bits_or_absolute_counts(self):
        before, after = (
            self.sample(),
            self.sample(monotonic=12.0, uptime_ticks=10200, rx_bytes=200, tx_bytes=500),
        )
        self.assertEqual(
            m.byte_rates(before, after),
            {"rx_bytes_per_second": 50.0, "tx_bytes_per_second": 150.0},
        )

    def test_zero_is_valid_only_for_two_real_unchanged_counter_samples(self):
        self.assertIsNone(m.byte_rates(None, self.sample()))
        value = m.byte_rates(self.sample(), self.sample(monotonic=12.0, uptime_ticks=10200))
        self.assertEqual(value, {"rx_bytes_per_second": 0.0, "tx_bytes_per_second": 0.0})

    def test_reset_or_wrap_does_not_fabricate_a_large_or_zero_rate(self):
        for change in ({"rx_bytes": 0}, {"tx_bytes": 0}, {"uptime_ticks": 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                m.byte_rates(self.sample(), self.sample(monotonic=12.0, **change))

    def test_identity_changes_cannot_be_compared_as_one_series(self):
        for change in ({"agent": "OTHER"}, {"interface": "Ethernet0/0"}, {"index": 3}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                m.byte_rates(self.sample(), self.sample(monotonic=12.0, **change))

    def test_stale_nonfinite_or_reversed_intervals_are_rejected(self):
        for timestamp in (0.0, 10.0, 71.0, float("nan"), float("inf")):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                m.byte_rates(self.sample(), self.sample(monotonic=timestamp))

    def test_unavailability_never_replaces_last_known_state_with_zero_metrics(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache = root / "telemetry-last.json"
            cache.write_text(json.dumps(self.sample()))
            original = cache.read_text()
            with (
                mock.patch.object(m, "ROOT", root),
                mock.patch.object(m, "collect", side_effect=m.Unavailable("agent_request_failed")),
            ):
                value = m.poll(True)
            self.assertFalse(value["available"])
            self.assertFalse(value["fresh"])
            self.assertIsNone(value["sample"])
            self.assertIsNone(value["byte_rates"])
            self.assertTrue(value["last_known_present"])
            self.assertEqual(cache.read_text(), original)

    def test_failed_positive_rate_check_does_not_advance_its_reference_sample(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "telemetry-auth-mode").write_text("good")
            cache = root / "telemetry-last.json"
            cache.write_text(json.dumps(self.sample()))
            original = cache.read_text()
            current = self.sample(monotonic=12.0, uptime_ticks=10200, rx_bytes=101, tx_bytes=200)
            with (
                mock.patch.object(m, "ROOT", root),
                mock.patch.object(m, "collect", return_value=current),
                self.assertRaises(AssertionError),
            ):
                m.report("rates")
            self.assertEqual(cache.read_text(), original)

    def test_incorrect_device_identity_is_not_unavailable_or_a_good_sample(self):
        def request(target, oid, **kwargs):
            if oid == m.wire.UPTIME:
                return 0, oid + " = Timeticks: (123) 0:00:01.23"
            return 0, oid + " = STRING: OTHER"

        with (
            mock.patch.object(m.wire, "request", side_effect=request),
            self.assertRaises(AssertionError),
        ):
            m.collect()


if __name__ == "__main__":
    unittest.main()
