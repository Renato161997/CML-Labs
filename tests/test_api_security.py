import importlib.util
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / "examples/automation"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("api_security", SOURCE / "api_security.py")
security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(security)
sys.path.pop(0)


class RejectionEvidence(unittest.TestCase):
    def client_fixture(self):
        client = types.ModuleType("client")
        state = {"jobs": []}
        client.get = Mock(
            side_effect=lambda path: (
                {"marker": security.MARKER}
                if path == "/health"
                else {"jobs": list(state["jobs"]), "events": []}
            )
        )
        client.observed = Mock()
        client.request = Mock()
        return client, state

    def test_every_rejection_keeps_history_checks_and_bounded_device_windows(self):
        client, _ = self.client_fixture()
        responses = [(case[5], {"error": case[6]}) for case in security.cases()]
        with (
            patch.dict(sys.modules, {"client": client}),
            patch.object(security, "wire", side_effect=responses),
            patch.object(security.time, "sleep"),
        ):
            result = security.exercise("matrix")
        self.assertEqual(result["wire_rejections"], 15)
        self.assertEqual(result["device_observation_windows"], 4)
        self.assertEqual(client.observed.call_count, 4)
        self.assertEqual(
            sum(call.args == ("/v1/history",) for call in client.get.call_args_list), 16
        )

    def test_a_rejected_request_that_changes_history_fails(self):
        client, state = self.client_fixture()

        def bad_server(*_):
            state["jobs"].append("unexpected")
            return 401, {"error": "authentication_required"}

        with (
            patch.dict(sys.modules, {"client": client}),
            patch.object(security, "wire", side_effect=bad_server),
            patch.object(security.time, "sleep"),
            self.assertRaises(AssertionError),
        ):
            security.exercise("matrix")

    def test_unavailable_device_is_not_a_successful_observation(self):
        client, _ = self.client_fixture()
        client.observed.side_effect = AssertionError("backend unavailable")
        with (
            patch.dict(sys.modules, {"client": client}),
            patch.object(security, "wire") as wire,
            patch.object(security.time, "sleep"),
            self.assertRaises(AssertionError),
        ):
            security.exercise("matrix")
        wire.assert_not_called()

    def test_guest_module_names_resolve_before_any_network_call(self):
        scripts = SOURCE.parents[1] / "scripts"
        sys.path.insert(0, str(scripts))
        try:
            spec = importlib.util.spec_from_file_location(
                "security_embedding", scripts / "embed_webhook.py"
            )
            embedding = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(embedding)
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory() as directory:
            for target, source in embedding.NATIVE_PROFILES["native-iosxe-api-security"][
                "CLIENT"
            ].items():
                (Path(directory) / Path(target).name).write_bytes(
                    (SOURCE.parents[1] / source).read_bytes()
                )
            code = (
                "import s, client\nfrom unittest.mock import patch\n"
                'with patch.object(client, "get", side_effect=RuntimeError("network-guard")):\n'
                ' try: s.exercise("matrix")\n'
                ' except RuntimeError as exc: assert str(exc) == "network-guard"\n'
                ' else: raise AssertionError("Network guard was not reached")\n'
            )
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_rejection(self):
        security.rejection(
            401, {"error": "authentication_required"}, 401, "authentication_required"
        )

    def test_success_does_not_qualify(self):
        with self.assertRaises(AssertionError):
            security.rejection(
                200, {"error": "authentication_required"}, 401, "authentication_required"
            )

    def test_rejection_cannot_leak_device_or_job(self):
        for field in ("facts", "job", "token", "traceback"):
            with self.subTest(field=field), self.assertRaises(AssertionError):
                security.rejection(
                    401,
                    {"error": "authentication_required", field: {}},
                    401,
                    "authentication_required",
                )

    def test_unrelated_error_does_not_qualify(self):
        with self.assertRaises(AssertionError):
            security.rejection(
                401, {"error": "backend_unavailable"}, 401, "authentication_required"
            )

    def test_ambiguous_header_probe_preserves_both_fields(self):
        case = next(row for row in security.cases() if row[0] == "ambiguous-authentication")
        self.assertEqual([key for key, _ in case[3]], ["Authorization", "Authorization"])
        self.assertNotEqual(case[3][0][1], case[3][1][1])

    def test_duplicate_json_probe_is_not_just_invalid_json(self):
        case = next(row for row in security.cases() if row[0] == "duplicate-json-key")
        self.assertIsInstance(json.loads(case[4]), dict)
        with self.assertRaises(ValueError):
            security.decode(case[4])


class LocalFixturePolicy(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.path = self.root / "controller-approvals.json"
        self.path.write_text(json.dumps(security.approvals()), encoding="utf-8")
        self.root_patch = patch.object(security, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.root_patch.stop)

    def test_withdraw_and_restore_only_the_known_fixture(self):
        self.assertFalse(security.policy(False)["policy_enabled"])
        self.assertEqual(json.loads(self.path.read_text()), [])
        self.assertTrue(security.policy(True)["policy_enabled"])
        self.assertEqual(json.loads(self.path.read_text()), security.approvals())

    def test_unknown_policy_is_preserved(self):
        self.path.write_text('[{"foreign":"policy"}]', encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            security.policy(False)
        self.assertEqual(self.path.read_bytes(), before)

    def test_recovery_cannot_clobber_an_unknown_policy(self):
        with self.assertRaises(ValueError):
            security.policy(True)
        self.assertEqual(json.loads(self.path.read_text()), security.approvals())

    def test_duplicate_policy_fields_cannot_be_normalized_away(self):
        self.path.write_text('[{"request_id":"a","request_id":"b"}]', encoding="utf-8")
        with self.assertRaises(ValueError):
            security.policy(False)

    def test_existing_temporary_file_is_not_overwritten(self):
        temporary = self.root / "controller-approvals.next"
        temporary.write_text("unrelated", encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            security.policy(False)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(temporary.read_text(), "unrelated")

    def test_symlink_policy_is_refused(self):
        with (
            patch.object(Path, "is_symlink", return_value=True),
            self.assertRaises(PermissionError),
        ):
            security.policy(False)
