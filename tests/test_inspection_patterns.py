"""Regression checks against IOSvL2's multiple numeric statistics tables."""

import json
import re
import unittest
from pathlib import Path


class InspectionPatternTests(unittest.TestCase):
    def pattern(self, phase):
        plans = json.loads(
            (Path(__file__).parents[1] / "validation/checks.json").read_text(encoding="utf-8")
        )
        plan = next(v for k, v in plans.items() if k.endswith("/033-dhcp-snooping-dai.yaml"))
        step = next(s for s in plan["transitions"] if s["name"] == phase)
        return next(
            c["pattern"]
            for c in step["checks"]
            if c["command"] == "show ip arp inspection statistics vlan 10"
        )

    def output(
        self, dropped, dhcp_drops, acl_permits=0, probe_permits=0, forwarded=0, dhcp_permits=0
    ):
        return (
            "show ip arp inspection statistics vlan 10\n"
            " Vlan      Forwarded        Dropped     DHCP Drops      ACL Drops\n"
            " ----      ---------        -------     ----------      ---------\n"
            f"   10              {forwarded}              {dropped}              {dhcp_drops}              0\n\n"
            " Vlan   DHCP Permits    ACL Permits  Probe Permits   Source MAC Failures\n"
            " ----   ------------    -----------  -------------   -------------------\n"
            f"   10              {dhcp_permits}              {acl_permits}              {probe_permits}                     0\n"
            "SW1#\n"
        )

    def test_forwarded_traffic_alone_does_not_prove_dhcp_binding_permits(self):
        pattern = self.pattern("fresh legitimate ARP")
        self.assertIsNone(re.search(pattern, self.output(0, 0, forwarded=8), re.MULTILINE))
        self.assertIsNotNone(
            re.search(pattern, self.output(0, 0, forwarded=8, dhcp_permits=3), re.MULTILINE)
        )

    def test_zero_permit_table_cannot_hide_real_dhcp_drops(self):
        self.assertIsNone(
            re.search(self.pattern("fresh baseline counters"), self.output(5, 5), re.MULTILINE)
        )

    def test_other_permit_columns_cannot_be_mistaken_for_dhcp_drops(self):
        self.assertIsNone(
            re.search(
                self.pattern("static address impersonation"),
                self.output(0, 0, acl_permits=3, probe_permits=5),
                re.MULTILINE,
            )
        )


if __name__ == "__main__":
    unittest.main()
