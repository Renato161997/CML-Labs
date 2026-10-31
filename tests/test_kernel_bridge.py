import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "kernel_bridge",
    Path(__file__).resolve().parents[1] / "examples/virtualization/kernel_bridge.py",
)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
dynamic, port_vlan = bridge.dynamic, bridge.port_vlan


def port(data_vlan=10):
    return [
        {
            "ifname": "eth2",
            "vlans": [{"vlan": data_vlan, "flags": ["PVID", "Egress Untagged"]}, {"vlan": 99}],
        }
    ]


class BridgeObservationTests(unittest.TestCase):
    def test_shared_and_isolated_data_membership_preserve_tagged_control(self):
        port_vlan(port(), "eth2", 10)
        port_vlan(port(20), "eth2", 20)

    def test_a_leaked_data_vlan_cannot_pass_as_isolation(self):
        rows = port(20)
        rows[0]["vlans"].append({"vlan": 10})
        with self.assertRaises(AssertionError):
            port_vlan(rows, "eth2", 20)

    def test_control_path_must_remain_tagged(self):
        rows = port()
        rows[0]["vlans"][1]["flags"] = ["Egress Untagged"]
        with self.assertRaises(AssertionError):
            port_vlan(rows, "eth2", 10)

    def test_control_vlan_cannot_disappear(self):
        rows = port()
        rows[0]["vlans"].pop()
        with self.assertRaises(AssertionError):
            port_vlan(rows, "eth2", 10)

    def test_data_vlan_must_be_the_untagged_pvid(self):
        rows = port()
        rows[0]["vlans"][0]["flags"] = ["PVID"]
        with self.assertRaises(AssertionError):
            port_vlan(rows, "eth2", 10)

    def test_wrong_or_duplicate_port_cannot_supply_evidence(self):
        for rows in [port(), port() + port()]:
            with self.assertRaises(AssertionError):
                port_vlan(rows, "eth1" if len(rows) == 1 else "eth2", 10)

    def test_actual_dynamic_entry_identity(self):
        entry = {
            "ifname": "eth1",
            "mac": "02:00:00:00:00:01",
            "vlan": 10,
            "master": "br0",
            "state": "reachable",
        }
        self.assertTrue(dynamic(entry, "02:00:00:00:00:01", "eth1"))
        self.assertFalse(dynamic(entry, "02:00:00:00:00:02", "eth1"))
        self.assertFalse(dynamic(entry, "02:00:00:00:00:01", "eth2"))
        self.assertFalse(dynamic({**entry, "vlan": 99}, entry["mac"], "eth1"))

    def test_static_or_imported_mac_is_not_dynamic_learning(self):
        entry = {"ifname": "eth1", "mac": "02:00:00:00:00:01", "vlan": 10, "master": "br0"}
        for state in ["permanent", "static", "noarp"]:
            self.assertFalse(dynamic({**entry, "state": state}, entry["mac"], "eth1"))
        for flag in ["self", "extern_learn", "sticky"]:
            self.assertFalse(dynamic({**entry, "flags": [flag]}, entry["mac"], "eth1"))


if __name__ == "__main__":
    unittest.main()
