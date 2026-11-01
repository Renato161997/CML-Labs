import importlib.util
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / "examples/automation"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("event_client", SOURCE / "event_client.py")
client_probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_probe)
sys.path.pop(0)


class PublisherProofChecks(unittest.TestCase):
    def backend(self, history):
        backend = types.ModuleType("client")
        backend.get = Mock(side_effect=lambda path: {"pid": 100} if path == "/health" else history)
        backend.observed = Mock()
        backend.submit = Mock()
        return backend

    def test_each_wire_rejection_keeps_history_and_one_bounded_device_observation(self):
        history = {"jobs": [], "events": []}
        backend = self.backend(history)
        responses = [
            (expected, {"error": "rejected"}) for _, _, expected in client_probe.rejection_cases()
        ]
        responses.append((200, {"marker": client_probe.MARKER, "pid": 1 + 1}))
        with (
            patch.dict(sys.modules, {"client": backend}),
            patch.object(client_probe, "wire", side_effect=responses),
            patch.object(client_probe.time, "sleep"),
        ):
            value = client_probe.exercise("invalids")
        self.assertEqual(value["wire_rejections"], 6)
        self.assertEqual(backend.get.call_count, 7)
        backend.observed.assert_called_once_with(["198.18.0.2"])

    def test_signed_approval_rejection_is_checked_before_reporting_success(self):
        backend = self.backend({"jobs": [], "events": []})
        with (
            patch.dict(sys.modules, {"client": backend}),
            patch.object(
                client_probe, "wire", return_value=(403, {"error": "intent_not_approved"})
            ),
        ):
            self.assertTrue(
                client_probe.exercise("approval-denied")["valid_signature_is_not_approval"]
            )
        self.assertEqual(backend.get.call_count, 2)
        backend.observed.assert_called_once()

    def test_timeout_is_not_accepted_as_confirmed_gateway_shutdown(self):
        backend = self.backend({"jobs": [], "events": []})
        with (
            patch.dict(sys.modules, {"client": backend}),
            patch.object(client_probe, "wire", side_effect=TimeoutError()),
            self.assertRaises(TimeoutError),
        ):
            client_probe.exercise("gateway-down")
        backend.observed.assert_not_called()

    def test_unchanged_gateway_pid_cannot_pass_restart_evidence(self):
        state = {"gateway_pid": 200, "controller_pid": 100, "history": {"jobs": [], "events": []}}
        backend = self.backend(state["history"])
        with (
            patch.dict(sys.modules, {"client": backend}),
            patch.object(client_probe, "load", return_value=state),
            patch.object(client_probe, "gateway_health", return_value={"pid": 200}),
            self.assertRaises(AssertionError),
        ):
            client_probe.exercise("repeat-after-restart")
        backend.get.assert_not_called()

    def test_history_mutation_cannot_pass_duplicate_delivery_evidence(self):
        state = {"gateway_pid": 200, "controller_pid": 100, "history": {"jobs": [], "events": []}}
        backend = self.backend({"jobs": ["unexpected"], "events": []})
        with (
            patch.dict(sys.modules, {"client": backend}),
            patch.object(client_probe, "load", return_value=state),
            patch.object(client_probe, "gateway_health", return_value={"pid": 200}),
            patch.object(
                client_probe, "send", return_value={"replayed": True, "applied_now": False}
            ),
            self.assertRaises(AssertionError),
        ):
            client_probe.exercise("repeat")
        backend.observed.assert_not_called()

    def test_registered_tool_and_client_payload_names_bootstrap_in_clean_directories(self):
        root = SOURCE.parents[1]
        spec = importlib.util.spec_from_file_location(
            "embed_event_sources", root / "scripts/embed_webhook.py"
        )
        registry = importlib.util.module_from_spec(spec)
        with patch.object(sys, "path", [str(root / "scripts"), *sys.path]):
            spec.loader.exec_module(registry)
        for role, sources in registry.NATIVE_PROFILES["native-controller-events"].items():
            with self.subTest(role=role), tempfile.TemporaryDirectory() as directory:
                for destination, source in sources.items():
                    (Path(directory) / Path(destination).name).write_bytes(
                        (root / source).read_bytes()
                    )
                statement = "import event_gateway, client" + (
                    ", api_security" if role == "TOOLS" else ", event_client"
                )
                result = subprocess.run(
                    [sys.executable, "-c", statement],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
