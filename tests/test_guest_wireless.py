import errno
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "radio_probe", ROOT / "examples/wireless/radio_probe.py"
)
radio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radio)
spec = importlib.util.spec_from_file_location(
    "guest_probe", ROOT / "examples/wireless/guest_probe.py"
)
guest = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"radio_probe": radio}):
    spec.loader.exec_module(guest)


def rule():
    return {
        "priority": 12345,
        "src": "all",
        "dst": "198.18.20.0",
        "dstlen": 30,
        "iif": "wlan0",
        "action": "prohibit",
    }


class GuestPolicy(unittest.TestCase):
    def test_actual_rpdb_prefix_and_ingress_must_match(self):
        guest.rule_is_exact(rule())
        for key, value in [
            ("dstlen", 24),
            ("dst", "198.18.21.0"),
            ("iif", "ens2"),
            ("action", "unreachable"),
            ("src", "198.18.10.2"),
            ("priority", 0),
        ]:
            bad = rule()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                guest.rule_is_exact(bad)

    def test_inverse_and_extra_selectors_cannot_masquerade_as_full_policy(self):
        for key, value in [
            ("not", None),
            ("fwmark", "0x1"),
            ("uid_start", 0),
            ("oif", "ens2"),
            ("iif_detached", None),
        ]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                guest.rule_is_exact({**rule(), key: value})

    def test_priority_collision_is_not_silently_deleted(self):
        output = type("Output", (), {"stdout": json.dumps([rule(), rule()])})()
        with (
            patch.object(radio, "run_command", return_value=output),
            self.assertRaises(AssertionError),
        ):
            guest.policy_state()

    def test_response_needs_the_fresh_nonce_and_exact_endpoint_identity(self):
        value = {"marker": radio.MARKER, "role": "inside", "nonce": "a" * 32, "pid": 123}
        guest.response(value, "a" * 32, "inside")
        for changes in [
            {"nonce": "b" * 32},
            {"role": "ap"},
            {"marker": "other"},
            {"pid": True},
            {"extra": 1},
        ]:
            with self.subTest(changes=changes), self.assertRaises(AssertionError):
                guest.response({**value, **changes}, "a" * 32, "inside")

    def test_request_cannot_target_arbitrary_hosts_or_sources(self):
        for target, source in [("127.0.0.1", guest.GUEST), (guest.INSIDE, "203.0.113.2")]:
            with self.assertRaises(ValueError):
                guest.request(target, source)

    def test_partial_packets_cannot_pass_positive_or_negative_checks(self):
        output = type(
            "Output", (), {"stdout": "3 packets transmitted, 1 received", "returncode": 0}
        )()
        for received in (0, 3):
            with (
                patch.object(radio, "run_command", return_value=output),
                self.assertRaises(AssertionError),
            ):
                guest.ping(guest.INSIDE, "wlan0", received)

    def test_only_explicit_policy_boolean_is_accepted(self):
        for value in (1, "yes", None):
            with self.assertRaises(ValueError):
                guest.policy(value)

    def test_client_cannot_start_a_shared_endpoint(self):
        with self.assertRaises(ValueError):
            guest.make_server(("127.0.0.1", 0), "client")

    def test_refusal_timeout_and_reset_are_not_policy_enforcement_proof(self):
        for code in (errno.EHOSTUNREACH, errno.ENETUNREACH, errno.EACCES, errno.EPERM):
            guest.explicit_denial(OSError(code, "fixture"))
        for code in (errno.ECONNREFUSED, errno.ETIMEDOUT, errno.ECONNRESET, None, True):
            with self.assertRaises(AssertionError):
                guest.explicit_denial(OSError(code, "fixture"))


if __name__ == "__main__":
    unittest.main()
