import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from acceptance import execute_plan, validate_plan
from console_protocol import response_complete
from labtools import check_evidence, plan_digest


class Console:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.commands = []
        self.timeouts = []

    def command(self, command, timeout=18):
        self.commands.append(command)
        self.timeouts.append(timeout)
        return next(self.outputs)


CHECK = {
    "node": "R1",
    "command": "show ip route",
    "pattern": "via 198.18.0.2",
    "expectation": "Primary route is installed.",
    "attempts": 1,
}


class AcceptanceTests(unittest.TestCase):
    def test_transition_requires_its_structured_result_before_readback(self):
        step = {
            "name": "API change",
            "node": "R1",
            "commands": ["python3 change.py"],
            "command_pattern": '"status": "passed"',
            "checks": [CHECK],
        }
        plan = {"checks": [CHECK], "transitions": [step]}
        self.assertEqual(validate_plan(plan, {"R1"}), [])
        for result, succeeds in (
            ('{"status": "passed"}', True),
            ('{"status": "failed"}', False),
            ("Traceback: remote change did not complete", False),
        ):
            connection = Console(
                [
                    "show ip route\nvia 198.18.0.2",
                    "python3 change.py\n" + result,
                    "show ip route\nvia 198.18.0.2",
                ]
            )
            rows = []
            if succeeds:
                execute_plan(plan, lambda _, connection=connection: connection, rows.append)
                self.assertTrue(rows[1]["passed"])
            else:
                with self.assertRaises(AssertionError):
                    execute_plan(plan, lambda _, connection=connection: connection, rows.append)
                self.assertFalse(rows[-1]["passed"])
                self.assertEqual(len(connection.commands), 2)
        for invalid in ("", "[", None, 42):
            step["command_pattern"] = invalid
            self.assertTrue(validate_plan(plan, {"R1"}))

    def test_green_transition_flag_cannot_replace_observed_result(self):
        step = {
            "name": "API change",
            "node": "R1",
            "commands": ["python3 change.py"],
            "command_pattern": '"status": "passed"',
            "checks": [CHECK],
        }
        plan = {"checks": [CHECK], "transitions": [step]}
        rows = [
            {**CHECK, "phase": "baseline", "passed": True},
            {**CHECK, "phase": step["name"], "passed": True},
            {
                "kind": "configuration",
                "phase": step["name"],
                "node": "R1",
                "command": "python3 change.py",
                "output": "Traceback",
                "passed": True,
            },
        ]
        proof = {
            "sha256": "abc",
            "status": "passed",
            "test_lab_removed": True,
            "cml_version": "test",
            "plan_sha256": plan_digest(plan),
            "checks": rows,
        }
        errors = check_evidence(proof, "lab", "abc", "runtime", plan_digest(plan), plan)
        self.assertTrue(any("required result pattern" in error for error in errors))
        rows[-1]["output"] = '{"status": "passed"}'
        self.assertEqual(
            check_evidence(proof, "lab", "abc", "runtime", plan_digest(plan), plan), []
        )

    def test_slow_configuration_timeout_is_bounded_and_reaches_the_console(self):
        step = {
            "name": "initialize host key",
            "node": "R1",
            "commands": ["crypto key generate rsa modulus 2048"],
            "command_timeout": 30,
            "checks": [CHECK],
        }
        plan = {"checks": [CHECK], "transitions": [step]}
        self.assertEqual(validate_plan(plan, {"R1"}), [])
        connection = Console(
            [
                "show ip route\nvia 198.18.0.2",
                "crypto key generate rsa modulus 2048\nR1(config)#",
                "show ip route\nvia 198.18.0.2",
            ]
        )
        execute_plan(plan, lambda _: connection, lambda _: None)
        self.assertEqual(connection.timeouts, [18, 30, 18])
        for bad in (0, 61, "30"):
            step["command_timeout"] = bad
            self.assertTrue(validate_plan(plan, {"R1"}))

    def test_slow_protocol_can_use_its_bounded_convergence_window(self):
        connection = Console(["show ip route\nNo route"] * 20 + ["show ip route\nvia 198.18.0.2"])
        waits = []
        rows = []
        execute_plan(
            {"checks": [{**CHECK, "attempts": 21, "interval_seconds": 20}]},
            lambda _: connection,
            rows.append,
            sleep=waits.append,
        )
        self.assertEqual(waits, [20] * 20)
        self.assertTrue(rows[-1]["passed"])

    def test_log_tail_cannot_be_accepted_as_a_complete_command_echo(self):
        command = "show ip arp inspection statistics vlan 10"
        log = "*Oct 25 00:00:00.000: %SW_DAI-4-DHCP_SNOOPING_DENY: synthetic event])"
        self.assertFalse(response_complete(log + command + "\nCOUNTERS\nSW1#", command, "SW1"))
        self.assertTrue(
            response_complete(log + "\r\nSW1#" + command + "\r\nCOUNTERS\r\nSW1#", command, "SW1")
        )

    def test_asynchronous_prompt_before_echo_cannot_finish_a_response(self):
        self.assertFalse(response_complete("Sending three probes\nR1#", "end", "R1"))
        self.assertFalse(response_complete("%LINK interface shutdown\nR1#", "shutdown", "R1"))
        self.assertFalse(response_complete("%LINK changed\nR1#", "configure terminal", "R1"))
        self.assertFalse(
            response_complete(
                "R1#\nconfigure terminal\nEnter configuration", "configure terminal", "R1"
            )
        )
        self.assertTrue(
            response_complete(
                "%LINK changed\nR1#\nconfigure terminal\nR1(config)#", "configure terminal", "R1"
            )
        )
        self.assertTrue(
            response_complete("root@DEVBOX:~# echo OK\nOK\nroot@DEVBOX:~#", "echo OK", "DEVBOX")
        )

    def test_expected_backup_does_not_hide_a_still_present_primary(self):
        check = {**CHECK, "pattern": "198.18.1.2", "absent_pattern": "198.18.0.2"}
        rows = []
        with self.assertRaises(AssertionError):
            execute_plan(
                {"checks": [check]},
                lambda _: Console(["show ip route\n198.18.0.2\n198.18.1.2"]),
                rows.append,
            )
        self.assertFalse(rows[-1]["passed"])

    def test_transition_with_no_assertion_or_unknown_node_is_rejected(self):
        errors = validate_plan(
            {
                "checks": [CHECK],
                "transitions": [
                    {"name": "failure", "node": "UNKNOWN", "commands": ["shutdown"], "checks": []}
                ],
            },
            {"R1"},
        )
        self.assertGreaterEqual(len(errors), 2)

    def test_proof_cannot_skip_a_planned_failure_transition(self):
        plan = {
            "checks": [CHECK],
            "transitions": [
                {"name": "failure", "node": "R1", "commands": ["shutdown"], "checks": [CHECK]}
            ],
        }
        proof = {
            "sha256": "abc",
            "status": "passed",
            "test_lab_removed": True,
            "cml_version": "test",
            "plan_sha256": plan_digest(plan),
            "checks": [{**CHECK, "passed": True}],
        }
        errors = check_evidence(proof, "lab", "abc", "runtime", plan_digest(plan), plan)
        self.assertTrue(any("omits planned" in error for error in errors))

    def test_no_stale_console_or_invalid_cli_can_pass(self):
        for output in ("via 198.18.0.2", "show ip route\n% Invalid input via 198.18.0.2"):
            rows = []
            with self.assertRaises(AssertionError):
                execute_plan(
                    {"checks": [CHECK]}, lambda _, output=output: Console([output]), rows.append
                )
            self.assertFalse(rows[0]["passed"])

    def test_ordered_failure_recovery_checks_are_actually_executed(self):
        backup = {**CHECK, "pattern": "via 198.18.1.2"}
        plan = {
            "checks": [CHECK],
            "transitions": [
                {"name": "failover", "node": "R1", "commands": ["shutdown"], "checks": [backup]},
                {"name": "restore", "node": "R1", "commands": ["no shutdown"], "checks": [CHECK]},
            ],
        }
        connection = Console(
            [
                "show ip route\nvia 198.18.0.2",
                "shutdown\nR1(config-if)#",
                "show ip route\nvia 198.18.1.2",
                "no shutdown\nR1(config-if)#",
                "show ip route\nvia 198.18.0.2",
            ]
        )
        rows = []
        execute_plan(plan, lambda _, connection=connection: connection, rows.append)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["passed"] for r in rows))
        self.assertEqual(connection.commands.count("show ip route"), 3)

    def test_failed_transition_stops_before_recovery_claim(self):
        connection = Console(["show ip route\nvia 198.18.0.2", "shutdown\n% Incomplete command"])
        rows = []
        with self.assertRaises(AssertionError):
            execute_plan(
                {
                    "checks": [CHECK],
                    "transitions": [
                        {
                            "name": "failure",
                            "node": "R1",
                            "commands": ["shutdown"],
                            "checks": [CHECK],
                        }
                    ],
                },
                lambda _: connection,
                rows.append,
            )
        self.assertEqual(len(rows), 2)
        self.assertFalse(rows[-1]["passed"])

    def test_api_client_timeout_is_bounded_and_forwarded(self):
        check = dict(CHECK, command_timeout=60)
        plan = {"checks": [check]}
        self.assertEqual(validate_plan(plan, {"R1"}), [])
        connection = Console(["show ip route\nvia 198.18.0.2"])
        execute_plan(plan, lambda _: connection, lambda _: None)
        self.assertEqual(connection.timeouts, [60])
        for invalid in (True, 0, 91, "60"):
            self.assertTrue(
                validate_plan({"checks": [dict(check, command_timeout=invalid)]}, {"R1"})
            )


if __name__ == "__main__":
    unittest.main()
