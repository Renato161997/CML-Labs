import importlib.util
import struct
import sys
import unittest
from pathlib import Path

base = Path(__file__).resolve().parents[1] / "examples" / "security"
spec = importlib.util.spec_from_file_location("first_hop_wire", base / "first_hop_wire.py")
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
sys.modules["first_hop_wire"] = wire
spec = importlib.util.spec_from_file_location("first_hop_policy", base / "first_hop_policy.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SERVER_MAC = bytes.fromhex("020000000020")
BAD_MAC = bytes.fromhex("020000000066")


def message(kind, xid=7, lease=600):
    return wire.make_dhcp(kind, xid, SERVER_MAC if kind in (2, 5) else wire.CLIENT_MAC, lease=lease)


def data_frame(mac=wire.CLIENT_MAC, source=wire.LEASED):
    header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        21,
        1,
        0,
        64,
        253,
        0,
        wire.ip_bytes(source),
        wire.ip_bytes(wire.SERVER),
    )
    header = header[:10] + struct.pack("!H", wire.checksum(header)) + header[12:]
    return SERVER_MAC + mac + b"\x08\x00" + header + b"x"


def arp_frame(mac=wire.CLIENT_MAC, source=wire.LEASED):
    packet = (
        struct.pack("!HHBBH", 1, 0x0800, 6, 4, 2)
        + mac
        + wire.ip_bytes(source)
        + SERVER_MAC
        + wire.ip_bytes(wire.SERVER)
    )
    return (SERVER_MAC + mac + b"\x08\x06" + packet).ljust(60, b"\0")


class PortBoundInspection(unittest.TestCase):
    def bound(self, lease=600):
        gate = m.Gate()
        for side, kind in ((1, 1), (2, 2), (1, 3), (2, 5)):
            self.assertTrue(gate.process(side, message(kind, lease=lease), 0))
        return gate

    def test_only_complete_observed_trusted_port_dora_installs_a_binding(self):
        gate = self.bound()
        self.assertEqual(gate.binding["mac"], wire.CLIENT_MAC)
        self.assertEqual(gate.binding["ip"], wire.LEASED)
        self.assertEqual(gate.binding["port"], 1)
        self.assertEqual(gate.binding["lease"], 600)
        self.assertEqual(gate.counts["ack_learned"], 1)

    def test_trusted_ack_without_prior_discover_offer_request_cannot_admit(self):
        gate = m.Gate()
        self.assertFalse(gate.process(2, message(5), 0))
        self.assertIsNone(gate.binding)

    def test_valid_rogue_server_ack_on_untrusted_ingress_cannot_replace_binding(self):
        gate = self.bound()
        old = dict(gate.binding)
        self.assertFalse(gate.process(1, message(5, lease=3), 1))
        self.assertEqual(gate.binding, old)
        self.assertEqual(gate.counts["untrusted_server_drop"], 1)

    def test_transaction_mismatch_or_expired_pending_state_cannot_learn(self):
        for xid, now in ((8, 0), (7, 21)):
            gate = m.Gate()
            self.assertTrue(gate.process(1, message(1), 0))
            self.assertFalse(gate.process(2, message(2, xid=xid), now))
            self.assertIsNone(gate.binding)

    def test_client_request_from_the_trusted_port_cannot_create_pending_state(self):
        gate = m.Gate()
        self.assertFalse(gate.process(2, message(1), 0))
        self.assertIsNone(gate.pending)

    def test_inconsistent_lease_offer_and_ack_do_not_create_admission(self):
        gate = m.Gate()
        for side, kind in ((1, 1), (2, 2), (1, 3)):
            self.assertTrue(gate.process(side, message(kind), 0))
        self.assertFalse(gate.process(2, message(5, lease=3), 0))
        self.assertIsNone(gate.binding)

    def test_real_source_binding_allows_only_matching_ip_and_mac(self):
        gate = self.bound()
        self.assertTrue(gate.process(1, data_frame(), 1))
        self.assertFalse(gate.process(1, data_frame(source="198.18.10.11"), 1))
        self.assertFalse(gate.process(1, data_frame(mac=BAD_MAC), 1))
        self.assertEqual(gate.counts["ip_binding_drop"], 2)

    def test_arp_sender_binding_is_independent_of_ipv4_source_filter(self):
        gate = self.bound()
        self.assertTrue(gate.process(1, arp_frame(), 1))
        self.assertFalse(gate.process(1, arp_frame(mac=BAD_MAC), 1))
        self.assertFalse(gate.process(1, arp_frame(source="198.18.10.11"), 1))
        self.assertEqual(gate.counts["arp_binding_drop"], 2)
        self.assertEqual(gate.counts["ip_binding_drop"], 0)

    def test_stale_holder_with_same_ip_and_mac_is_blocked_at_actual_lease_expiry(self):
        gate = self.bound(lease=3)
        self.assertTrue(gate.process(1, data_frame(), 2.9))
        self.assertFalse(gate.process(1, data_frame(), 3.0))
        self.assertIsNone(gate.binding)
        self.assertEqual(gate.counts["lease_expired"], 1)
        self.assertEqual(gate.last_lease, 3)

    def test_trusted_data_and_legitimate_dhcp_reacquisition_still_work_after_expiry(
        self,
    ):
        gate = self.bound(lease=3)
        gate.expire(4)
        self.assertTrue(gate.process(2, data_frame(mac=SERVER_MAC, source=wire.SERVER), 4))
        for side, kind in ((1, 1), (2, 2), (1, 3), (2, 5)):
            self.assertTrue(gate.process(side, message(kind, xid=9), 5))
        self.assertTrue(gate.process(1, data_frame(), 5))
        self.assertEqual(gate.counts["ack_learned"], 2)

    def test_replayed_ack_cannot_extend_the_original_lease(self):
        gate = self.bound(lease=3)
        self.assertFalse(gate.process(2, message(5, lease=3), 2))
        self.assertFalse(gate.process(1, data_frame(), 3.1))

    def test_unknown_ethernet_and_malformed_packets_are_not_forwarded(self):
        gate = self.bound()
        self.assertFalse(gate.process(1, b"incomplete", 1))
        self.assertFalse(
            gate.process(1, SERVER_MAC + wire.CLIENT_MAC + b"\x86\xdd" + b"\0" * 40, 1)
        )
        self.assertEqual(gate.counts["malformed_drop"], 1)
        self.assertEqual(gate.counts["unsupported_drop"], 1)


if __name__ == "__main__":
    unittest.main()
