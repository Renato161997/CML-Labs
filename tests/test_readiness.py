import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from readiness import establish_ios_prompt, running_node_states, verify_unconfirmed_consoles


class ReadinessTests(unittest.TestCase):
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
