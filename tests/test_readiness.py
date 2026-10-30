import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from readiness import (
    establish_ios_privilege,
    establish_ios_prompt,
    running_node_states,
    verify_unconfirmed_consoles,
)


class ReadinessTests(unittest.TestCase):
    def test_interrupted_user_prompt_requires_a_clean_redraw(self):
        send = Mock()
        read = Mock(side_effect=["\nHUB>[OK]\n", "\nHUB>\n", "\nHUB#\n"])
        establish_ios_privilege("HUB", send, read)
        self.assertEqual(send.call_args_list, [call("\r"), call("\r"), call("enable\r")])

    def test_privilege_negotiation_waits_through_boot_chatter(self):
        send = Mock()
        read = Mock(
            side_effect=[
                "\nSPOKE-B>\n",
                "enable\n[OK]\n",
                "Boot message\nSPOKE-B>\n",
                "\nSPOKE-B#\n",
            ]
        )
        result = establish_ios_privilege("SPOKE-B", send, read)
        self.assertIn("SPOKE-B#", result)
        self.assertEqual(send.call_args_list, [call("\r"), call("enable\r")])

    def test_privilege_needs_a_fresh_exact_named_prompt(self):
        send = Mock()
        read = Mock(return_value="\nR1#\n")
        establish_ios_privilege("R1", send, read)
        send.assert_called_once_with("\r")
        read = Mock(return_value="Log mentions R1# while booting\nOTHER#\n")
        with (
            patch("readiness.time.monotonic", side_effect=[0, 0, 45]),
            self.assertRaises(TimeoutError),
        ):
            establish_ios_privilege("R1", Mock(), read)

    def test_privilege_negotiation_stops_at_a_credential_prompt(self):
        send = Mock()
        read = Mock(side_effect=["\nR1>\n", "\nPassword: "])
        with self.assertRaises(PermissionError):
            establish_ios_privilege("R1", send, read)
        self.assertEqual(send.call_args_list, [call("\r"), call("enable\r")])
        for invalid in (0, 91, True, "45"):
            with self.assertRaises(ValueError):
                establish_ios_privilege("R1", send, read, timeout=invalid)

    def test_iosv_cold_autoconfiguration_can_finish_after_four_minutes(self):
        send = Mock()
        read = Mock(return_value="\nR1>\n")
        with patch("readiness.time.monotonic", side_effect=[0, 260]):
            result = establish_ios_prompt("R1", "Autoconfiguration\n", send, read, timeout=600)
        self.assertIn("R1>", result)
        for invalid in (0, 601, True, "600"):
            with self.assertRaises(ValueError):
                establish_ios_prompt("R1", "", send, read, timeout=invalid)

    def test_cold_ios_boot_waits_for_the_named_prompt(self):
        send = Mock()
        read = Mock(return_value="\r\nAPI>\r\n")
        result = establish_ios_prompt("API", "System initializing\n", send, read)
        self.assertIn("API>", result)
        send.assert_called_once_with("\r")
        read.assert_called_once()

    def test_another_prompt_or_boot_log_cannot_establish_readiness(self):
        send = Mock()
        read = Mock(return_value="OTHER#\nLog mentions API# while booting\n")
        with (
            patch("readiness.time.monotonic", side_effect=[0, 0, 240]),
            self.assertRaises(TimeoutError),
        ):
            establish_ios_prompt("API", "Booting\n", send, read)
        send.assert_called_once_with("\r")

    def test_empty_or_nonrunning_topology_cannot_start_guest_checks(self):
        self.assertIsNone(running_node_states([]))
        for state in ("STOPPED", "DEFINED_ON_CORE", "QUEUED", "UNKNOWN"):
            self.assertIsNone(running_node_states([SimpleNamespace(label="R1", state=state)]))

    def test_started_state_is_preserved_and_requires_a_real_console(self):
        states = running_node_states(
            [
                SimpleNamespace(label="SW1", state="STARTED"),
                SimpleNamespace(label="R1", state="BOOTED"),
            ]
        )
        observed = []
        self.assertEqual(states, {"SW1": "STARTED", "R1": "BOOTED"})
        self.assertEqual(verify_unconfirmed_consoles(states, observed.append), ["SW1"])
        self.assertEqual(observed, ["SW1"])

    def test_failed_console_establishment_cannot_be_reported_as_ready(self):
        def unavailable(_):
            raise TimeoutError("Expected privileged prompt did not appear")

        with self.assertRaises(TimeoutError):
            verify_unconfirmed_consoles({"SW1": "STARTED"}, unavailable)
        with self.assertRaises(RuntimeError):
            verify_unconfirmed_consoles({"SW1": "STOPPED"}, lambda _: None)

    def test_duplicate_labels_cannot_hide_an_unverified_guest(self):
        with self.assertRaises(RuntimeError):
            running_node_states(
                [
                    SimpleNamespace(label="SW1", state="STARTED"),
                    SimpleNamespace(label="SW1", state="BOOTED"),
                ]
            )


if __name__ == "__main__":
    unittest.main()
