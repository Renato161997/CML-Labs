import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples/visibility"))
from correlate import correlate


class SyslogCorrelationTest(unittest.TestCase):
    def event(self, message, stamp, source="198.18.1.1"):
        return {"message": message, "source": source, "received_monotonic": stamp}

    def deny(self, stamp=100, source="198.18.1.1"):
        return self.event(
            "%SEC-6-IPACCESSLOGDP: list CML-DENY denied icmp 198.18.0.2 -> 192.0.2.1", stamp, source
        )

    def disabled(self, stamp=110, source="198.18.1.1"):
        return self.event(
            "%LINK-5-CHANGED: Interface Loopback1, changed state to administratively down",
            stamp,
            source,
        )

    def test_two_actual_families_on_one_sender_correlate(self):
        report = correlate([self.deny(), self.disabled()], "198.18.1.1")
        self.assertEqual(report["correlation_count"], 1)

    def test_single_family_is_not_an_incident(self):
        self.assertEqual(
            correlate([self.deny(), self.deny(101)], "198.18.1.1")["correlation_count"], 0
        )

    def test_other_sender_and_stale_events_do_not_correlate(self):
        for rows in (
            [self.deny(), self.disabled(source="198.18.1.9")],
            [self.deny(), self.disabled(300)],
        ):
            with self.subTest(rows=rows):
                self.assertEqual(correlate(rows, "198.18.1.1")["correlation_count"], 0)

    def test_truncated_record_cannot_create_an_incident(self):
        deny = self.deny()
        deny["truncated"] = True
        self.assertEqual(correlate([deny, self.disabled()], "198.18.1.1")["correlation_count"], 0)
