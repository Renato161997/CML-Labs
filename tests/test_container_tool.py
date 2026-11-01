import copy
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "container_tool",
    Path(__file__).resolve().parents[1] / "examples" / "automation" / "container_tool.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class KernelIdentity(unittest.TestCase):
    TEXT = "Uid:\t65534 65534 65534 65534\nGid:\t65534 65534 65534 65534\nGroups:\nCapInh:\t00000000\nCapPrm:\t00000000\nCapEff:\t00000000\nCapAmb:\t00000000\nNoNewPrivs:\t1\n"

    def test_actual_kernel_format_requires_all_identity_fields(self):
        self.assertTrue(m.unprivileged(m.kernel_identity(self.TEXT)))
        for bad in (
            self.TEXT.replace("CapAmb:", "Other:"),
            self.TEXT.replace("NoNewPrivs:\t1", "NoNewPrivs:\t3"),
            self.TEXT.replace("Uid:\t65534 65534 65534 65534", "Uid:\t65534"),
        ):
            with self.subTest(bad=bad), self.assertRaises((KeyError, ValueError)):
                m.kernel_identity(bad)

    def test_remaining_group_root_identity_or_capability_cannot_pass(self):
        original = m.kernel_identity(self.TEXT)
        for key, value in [
            ("uid", [65534, 65534, 0, 65534]),
            ("gid", [0] * 4),
            ("groups", [0]),
            ("no_new_privs", 0),
        ]:
            with self.subTest(key=key):
                self.assertFalse(m.unprivileged({**original, key: value}))
        for name in ("CapEff", "CapPrm", "CapInh", "CapAmb"):
            candidate = copy.deepcopy(original)
            candidate["caps"][name] = 1 << 12
            self.assertFalse(m.unprivileged(candidate))

    def test_drop_sets_no_new_privileges_before_all_credential_changes(self):
        order = mock.Mock()
        libc = mock.Mock()
        libc.prctl.side_effect = lambda *a: order.nnp(*a) or 0
        order.nnp.return_value = 0
        with (
            mock.patch.object(m.ctypes, "CDLL", return_value=libc),
            mock.patch.object(m.os, "setgroups", order.groups, create=True),
            mock.patch.object(m.os, "setgid", order.gid, create=True),
            mock.patch.object(m.os, "setuid", order.uid, create=True),
        ):
            m.demote()
        self.assertEqual(
            order.mock_calls,
            [
                mock.call.nnp(38, 1, 0, 0, 0),
                mock.call.groups([]),
                mock.call.gid(65534),
                mock.call.uid(65534),
            ],
        )

    def test_failed_no_new_privileges_cannot_continue_to_a_uid_change(self):
        libc = mock.Mock()
        libc.prctl.return_value = -1
        with (
            mock.patch.object(m.ctypes, "CDLL", return_value=libc),
            mock.patch.object(m.os, "setuid", create=True) as uid,
            self.assertRaises(OSError),
        ):
            m.demote()
        uid.assert_not_called()


class PhaseEvidence(unittest.TestCase):
    def good(self):
        return {
            "kernel_unprivileged": True,
            "root_regain_denied": True,
            "root_sentinel_readable": False,
            "owned_result_written_and_removed": True,
            "api": {
                "accepted": True,
                "wire_status": 200,
                "body": {"interface": {"name": "eth1", "carrier": True}},
            },
        }

    def test_complete_baseline_is_accepted(self):
        self.assertEqual(m.verified("baseline", self.good())["status"], "passed")

    def test_unknown_phase_cannot_become_a_baseline(self):
        with self.assertRaises(ValueError):
            m.verified("other-phase", self.good())

    def test_missing_or_non_boolean_privilege_evidence_fails(self):
        for key in (
            "kernel_unprivileged",
            "root_regain_denied",
            "owned_result_written_and_removed",
        ):
            for value in (False, 1, None):
                with (
                    self.subTest(key=key, value=value),
                    self.assertRaises(AssertionError),
                ):
                    m.verified("baseline", {**self.good(), key: value})

    def test_permission_fault_must_change_an_actual_read_outcome(self):
        with self.assertRaises(AssertionError):
            m.verified("readable", self.good())
        value = {**self.good(), "root_sentinel_readable": True}
        self.assertEqual(m.verified("readable", value)["status"], "passed")
        with self.assertRaises(AssertionError):
            m.verified("baseline", value)

    def test_no_key_phase_requires_a_real_documented_401(self):
        for response in (
            {"accepted": False, "reason": "unusable_response"},
            {
                "accepted": True,
                "wire_status": 200,
                "body": {"error": "authentication_required"},
            },
        ):
            with self.subTest(response=response), self.assertRaises(AssertionError):
                m.verified("no-key", {**self.good(), "api": response})
        response = {
            "accepted": True,
            "wire_status": 401,
            "body": {"error": "authentication_required"},
        }
        self.assertEqual(m.verified("no-key", {**self.good(), "api": response})["status"], "passed")

    def test_source_drift_is_not_inferred_from_a_network_failure(self):
        for phase, reason in (
            ("schema", "schema_violation"),
            ("media", "unexpected_media"),
        ):
            response = {"accepted": False, "reason": reason}
            self.assertEqual(
                m.verified(phase, {**self.good(), "api": response})["status"], "passed"
            )
            with self.assertRaises(AssertionError):
                m.verified(
                    phase,
                    {
                        **self.good(),
                        "api": {"accepted": False, "reason": "unusable_response"},
                    },
                )

    def test_network_success_still_requires_actual_carrier_up(self):
        response = {
            "accepted": True,
            "wire_status": 200,
            "body": {"interface": {"name": "eth1", "carrier": False}},
        }
        with self.assertRaises(AssertionError):
            m.verified("baseline", {**self.good(), "api": response})


if __name__ == "__main__":
    unittest.main()
