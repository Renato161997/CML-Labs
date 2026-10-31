import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "examples/wireless"
spec = importlib.util.spec_from_file_location("radio_probe", SOURCE / "radio_probe.py")
radio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radio)
spec = importlib.util.spec_from_file_location("vlan_probe", SOURCE / "vlan_probe.py")
vlan = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"radio_probe": radio}):
    spec.loader.exec_module(vlan)


def links():
    return {
        "br0": {"flags": ["UP"], "linkinfo": {"info_kind": "bridge"}},
        "wlan0": {"master": "br0"},
        "v10": {
            "master": "br0",
            "link": "ens2",
            "flags": ["UP"],
            "linkinfo": {"info_kind": "vlan", "info_data": {"id": 10}},
        },
        "v20": {
            "link": "ens2",
            "flags": ["UP"],
            "linkinfo": {"info_kind": "vlan", "info_data": {"id": 20}},
        },
    }


class WirelessVlan(unittest.TestCase):
    def test_mapping_requires_the_actual_tagged_uplink(self):
        self.assertEqual(vlan.mapping(links(), 10)["uplink_vlan"], 10)
        bad = links()
        bad["v10"]["linkinfo"]["info_data"]["id"] = 20
        with self.assertRaises(AssertionError):
            vlan.mapping(bad, 10)
        for field, value in [("link", "other0"), ("master", None), ("flags", [])]:
            bad = links()
            bad["v10"][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                vlan.mapping(bad, 10)

    def test_both_uplinks_cannot_forward_the_wlan_at_once(self):
        bad = links()
        bad["v20"]["master"] = "br0"
        with self.assertRaises(AssertionError):
            vlan.mapping(bad, 10)
        bad = links()
        del bad["v10"]["master"]
        bad["v20"]["master"] = "br0"
        self.assertEqual(vlan.mapping(bad, 20)["uplink_vlan"], 20)
        with self.assertRaises(AssertionError):
            vlan.mapping(bad, 10)

    def test_missing_radio_bridge_and_unexpected_vlans_are_rejected(self):
        for bad in [{}, {**links(), "v30": {}}]:
            with self.assertRaises(ValueError):
                vlan.mapping(bad, 10)
        with self.assertRaises(ValueError):
            vlan.mapping(links(), True)
        bad = links()
        bad["wlan0"]["master"] = "other"
        with self.assertRaises(AssertionError):
            vlan.mapping(bad, 10)

    def test_negative_control_cannot_remove_or_change_the_client_address(self):
        rows = [
            {
                "ifname": "wlan0",
                "flags": ["UP"],
                "addr_info": [{"family": "inet", "local": vlan.CLIENT, "prefixlen": 24}],
            }
        ]
        vlan.client_address(rows)
        for values in [
            [],
            [{"family": "inet", "local": "198.18.20.2", "prefixlen": 24}],
            rows[0]["addr_info"] * 2
            + [{"family": "inet", "local": "198.18.50.2", "prefixlen": 24}],
        ]:
            bad = copy.deepcopy(rows)
            bad[0]["addr_info"] = values
            with self.assertRaises(AssertionError):
                vlan.client_address(bad)

    def test_partial_replies_are_neither_success_nor_verified_absence(self):
        for result in [
            SimpleNamespace(returncode=0, stdout="3 packets transmitted, 1 received"),
            SimpleNamespace(returncode=1, stdout="2 packets transmitted, 0 received"),
        ]:
            with (
                patch.object(radio, "run_command", return_value=result),
                self.assertRaises(AssertionError),
            ):
                vlan.ping(vlan.TARGET, "wlan0")

    def test_negative_forwarding_control_still_requires_radio_association(self):
        with (
            patch.object(
                radio, "snapshot", return_value=({"wpa_state": "DISCONNECTED"}, "Not connected.")
            ),
            self.assertRaises(AssertionError),
        ):
            vlan.associated({"role": "client", "auth": "open", "ssid": "CML-CCNA014"})

    def test_interface_output_must_be_for_the_selected_device(self):
        result = SimpleNamespace(returncode=0, stdout=json.dumps([{"ifname": "other"}]))
        with (
            patch.object(radio, "run_command", return_value=result),
            self.assertRaises(AssertionError),
        ):
            vlan.interface("v10")
