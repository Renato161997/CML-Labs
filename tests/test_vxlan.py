import importlib.util
import ipaddress
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "vxlan_probe", Path(__file__).resolve().parents[1] / "examples/virtualization/vxlan_probe.py"
)
vx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vx)


def ip(src, dst, protocol, payload, ttl=64):
    return (
        struct.pack(
            "!BBHHHBBH4s4s",
            0x45,
            0,
            20 + len(payload),
            1,
            0,
            ttl,
            protocol,
            0,
            ipaddress.IPv4Address(src).packed,
            ipaddress.IPv4Address(dst).packed,
        )
        + payload
    )


def frame(vni=100, ttl=64, echo=False, destination="198.18.0.2"):
    mac = bytes.fromhex("020000000001")
    if echo:
        payload = ip(vx.DATA_LEFT, vx.DATA_RIGHT, 1, struct.pack("!BBHHH", 8, 0, 0, 1, 1))
        inner = mac * 2 + b"\x08\0" + payload
    else:
        payload = (
            struct.pack("!HHBBH", 1, 0x800, 6, 4, 1)
            + mac
            + ipaddress.IPv4Address(vx.DATA_LEFT).packed
            + bytes(6)
            + ipaddress.IPv4Address(vx.DATA_RIGHT).packed
        )
        inner = mac * 2 + b"\x08\x06" + payload
    tunnel = b"\x08\0\0\0" + vni.to_bytes(3, "big") + b"\0" + inner
    udp = struct.pack("!HHHH", 53000, 4789, 8 + len(tunnel), 0) + tunnel
    return mac * 2 + b"\x08\0" + ip("198.18.0.1", destination, 17, udp, ttl)


class WireObservation(unittest.TestCase):
    def test_invalid_echo_code_is_not_selected(self):
        bad = bytearray(frame(echo=True))
        bad[85] = 1
        self.assertIsNone(vx.inspect(bad, "198.18.0.1", "198.18.0.2"))

    def test_actual_header_fields_and_inner_arp(self):
        self.assertEqual(
            vx.inspect(frame(), "198.18.0.1", "198.18.0.2"),
            {"vni": 100, "ttl": 64, "kind": "arp-request"},
        )

    def test_routed_ttl_is_observed_not_replaced(self):
        result = vx.inspect(frame(ttl=63, destination="198.18.1.2"), "198.18.0.1", "198.18.1.2")
        self.assertEqual(result["ttl"], 63)

    def test_wire_vni_mismatch_remains_visible(self):
        self.assertEqual(vx.inspect(frame(vni=101), "198.18.0.1", "198.18.0.2")["vni"], 101)

    def test_inner_echo_request(self):
        self.assertEqual(
            vx.inspect(frame(echo=True), "198.18.0.1", "198.18.0.2")["kind"], "echo-request"
        )

    def test_wrong_underlay_peer_or_port_is_not_selected(self):
        self.assertIsNone(vx.inspect(frame(), "198.18.0.9", "198.18.0.2"))
        bad = bytearray(frame())
        bad[36:38] = struct.pack("!H", 9999)
        self.assertIsNone(vx.inspect(bad, "198.18.0.1", "198.18.0.2"))

    def test_udp_length_must_match_the_observed_payload(self):
        bad = bytearray(frame())
        bad[38:40] = struct.pack("!H", 8)
        with self.assertRaises(ValueError):
            vx.inspect(bad, "198.18.0.1", "198.18.0.2")

    def test_i_flag_and_reserved_octets_are_checked(self):
        for offset in [42, 43, 49]:
            bad = bytearray(frame())
            bad[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                vx.inspect(bad, "198.18.0.1", "198.18.0.2")

    def test_fragmented_or_truncated_ipv4_is_outside_scope(self):
        bad = bytearray(frame())
        bad[20:22] = struct.pack("!H", 0x2000)
        for data in [bad, frame()[:-1]]:
            with self.assertRaises(ValueError):
                vx.inspect(data, "198.18.0.1", "198.18.0.2")

    def test_unrelated_inner_arp_is_not_selected(self):
        bad = bytearray(frame())
        bad[78:82] = ipaddress.IPv4Address("198.19.0.9").packed
        self.assertIsNone(vx.inspect(bad, "198.18.0.1", "198.18.0.2"))

    def test_echo_reply_cannot_substitute_for_request_evidence(self):
        bad = bytearray(frame(echo=True))
        bad[84] = 0
        self.assertIsNone(vx.inspect(bad, "198.18.0.1", "198.18.0.2"))

    def test_declared_routed_gateways_and_direct_neighbors(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(vx, "ROOT", Path(directory)):
            for role, local, peer, gateway in [
                ("VTEP1", "198.18.0.1", "198.18.1.2", "198.18.0.2"),
                ("VTEP2", "198.18.1.2", "198.18.0.1", "198.18.1.1"),
            ]:
                (vx.ROOT / "vxlan-role").write_text(role)
                (vx.ROOT / "vxlan-mode").write_text("routed")
                value = vx.config()
                self.assertEqual(
                    (value["local"], value["peer"], value["gateway"]), (local, peer, gateway)
                )
            (vx.ROOT / "vxlan-mode").write_text("direct")
            self.assertIsNone(vx.config()["gateway"])

    def test_observed_kernel_port_schema_and_tampering(self):
        cfg = {
            "role": "VTEP1",
            "mode": "direct",
            "local": "198.18.0.1",
            "peer": "198.18.0.2",
            "gateway": None,
        }
        link = {
            "flags": ["UP"],
            "master": "br0",
            "linkinfo": {
                "info_kind": "vxlan",
                "info_data": {
                    "id": 100,
                    "local": cfg["local"],
                    "remote": cfg["peer"],
                    "port": 4789,
                    "ttl": 64,
                },
            },
        }
        address = {"addr_info": [{"family": "inet", "local": cfg["local"]}]}
        route = {"dev": "eth1"}
        ports = [
            {"ifname": name, "state": "forwarding", "master": "br0"} for name in ("eth2", "vx0")
        ]

        def observe():
            return patch.object(vx, "read", side_effect=[[link], [address], [route], ports])

        with observe(), patch.object(vx.os, "uname", create=True) as uname:
            uname.return_value.release = "host-unit-only"
            self.assertEqual(vx.state(cfg, 100)["vni"], 100)
        for key, bad in [("port", 8472), ("ttl", 63), ("remote", "198.18.0.9"), ("id", 99)]:
            before = link["linkinfo"]["info_data"][key]
            link["linkinfo"]["info_data"][key] = bad
            with self.subTest(key=key), observe(), self.assertRaises(AssertionError):
                vx.state(cfg, 100)
            link["linkinfo"]["info_data"][key] = before

    def test_unknown_role_and_mode_are_refused(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(vx, "ROOT", Path(directory)):
            for role, mode in [("foreign", "direct"), ("VTEP1", "unknown")]:
                (vx.ROOT / "vxlan-role").write_text(role)
                (vx.ROOT / "vxlan-mode").write_text(mode)
                with self.assertRaises(AssertionError):
                    vx.config()


if __name__ == "__main__":
    unittest.main()
