import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "examples/management"))
from snmp_identity_probe import probe


class IdentityTests(unittest.TestCase):
    def test_domain_name_must_match_exactly_and_wrong_key_must_fail(self):
        uptime = (0, "Timeticks: (123) 00:00:01")
        with patch(
            "snmp_identity_probe.request",
            side_effect=[
                uptime,
                (0, 'STRING: "R1.lab.example"'),
                (1, "authentication failure"),
                uptime,
            ],
        ):
            self.assertEqual(probe("198.18.1.1", "healthy", "R1.lab.example")["status"], "passed")
        for identity in ("R1", "R1.lab.example.evil", "OTHER.lab.example"):
            with (
                patch(
                    "snmp_identity_probe.request",
                    side_effect=[uptime, (0, "STRING: " + identity)],
                ),
                self.assertRaises(RuntimeError),
            ):
                probe("198.18.1.1", "healthy", "R1.lab.example")
