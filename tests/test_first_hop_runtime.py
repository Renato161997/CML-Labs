import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

base = Path(__file__).resolve().parents[1] / "examples" / "security"
for name in ("first_hop_wire", "first_hop_policy", "first_hop_runtime"):
    spec = importlib.util.spec_from_file_location(name, base / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
m = sys.modules["first_hop_runtime"]


class LivePeerSafety(unittest.TestCase):
    def test_late_positive_train_cannot_be_accepted_as_timely_recovery(self):
        with (
            mock.patch.object(m, "ping", return_value=3),
            mock.patch.object(m.time, "monotonic", side_effect=[0, 16]),
            self.assertRaises(AssertionError),
        ):
            m.data_good()

    def test_incomplete_ping_is_not_zero_received(self):
        with (
            mock.patch.object(
                m,
                "run",
                return_value=subprocess.CompletedProcess([], 2, "socket error", ""),
            ),
            self.assertRaises(ValueError),
        ):
            m.ping()

    def test_good_data_requires_two_complete_consecutive_packet_trains(self):
        with (
            mock.patch.object(m, "ping", side_effect=[3, 2, 3, 3]) as ping,
            mock.patch.object(m.time, "monotonic", return_value=0),
            mock.patch.object(m.time, "sleep"),
        ):
            self.assertEqual(m.data_good()["consecutive_complete_trains"], 2)
        self.assertEqual(ping.call_count, 4)

    def test_control_route_is_removed_even_when_negative_observation_fails(self):
        with (
            mock.patch.object(m, "run") as command,
            mock.patch.object(m, "ping", side_effect=ValueError("incomplete")),
            self.assertRaises(ValueError),
        ):
            m.control_no_bypass()
        self.assertEqual(
            command.call_args_list[-1].args[0],
            [
                "ip",
                "route",
                "del",
                m.wire.SERVER + "/32",
                "via",
                "198.18.99.1",
                "dev",
                "eth2",
            ],
        )

    def test_spoofed_secondary_address_is_removed_even_when_ping_raises(self):
        with (
            mock.patch.object(m, "run") as command,
            mock.patch.object(m, "ping", side_effect=TimeoutError),
            self.assertRaises(TimeoutError),
        ):
            m.spoof_ip()
        self.assertEqual(
            command.call_args_list[-1].args[0],
            ["ip", "addr", "del", "198.18.10.11/24", "dev", "eth1"],
        )

    def test_wrong_transaction_and_outgoing_copy_cannot_satisfy_actual_ack_receive(
        self,
    ):
        server_mac = bytes.fromhex("020000000020")
        wrong = m.wire.make_dhcp(5, 99, server_mac)
        right = m.wire.make_dhcp(5, 7, server_mac)
        sock = mock.Mock()
        sock.recvfrom.side_effect = [
            (wrong, ("eth1", 0, 1)),
            (right, ("eth1", 0, 4)),
            (right, ("eth1", 0, 1)),
        ]
        with (
            mock.patch.object(m.time, "monotonic", return_value=0),
            mock.patch.object(m.select, "select", return_value=([sock], [], [])),
        ):
            self.assertEqual(m.receive(sock, 5, 7, 1)["xid"], 7)
        self.assertEqual(sock.recvfrom.call_count, 3)

    def test_no_matching_wire_ack_means_no_kernel_ip_installation(self):
        sock = mock.MagicMock()
        sock.__enter__.return_value = sock
        with (
            mock.patch.object(m, "role", return_value="CLIENT"),
            mock.patch.object(m, "mac", return_value=m.wire.CLIENT_MAC),
            mock.patch.object(m, "channel", return_value=sock),
            mock.patch.object(m, "receive", side_effect=TimeoutError) as receive,
            mock.patch.object(m, "run") as command,
            self.assertRaises(TimeoutError),
        ):
            m.acquire()
        self.assertEqual(receive.call_count, 3)
        command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
