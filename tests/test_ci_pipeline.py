import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

base = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "policy_code", base / "examples/security/policy_code.py"
)
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)
sys.modules["policy_code"] = compiler
spec = importlib.util.spec_from_file_location(
    "ci_pipeline", base / "examples/automation/ci_pipeline.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RealLocalGit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = mock.patch.object(m, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        (self.root / "ci-repo").mkdir()
        m.git("init", "--initial-branch=main", "--object-format=sha1")
        m.git("config", "user.name", "CML Test")
        m.git("config", "user.email", "test@example.test")
        self.revision = m.commit(compiler.intent(2, "allow"))
        raw = m.source(self.revision)
        body = compiler.compile_policy(compiler.intent(2, "allow"))
        self.bundle = {
            "commit": self.revision,
            "source_sha256": m.digest(raw),
            "intent": compiler.intent(2, "allow"),
            "body": body,
            "body_sha256": m.digest(body.encode()),
            "tests_run": 8,
        }
        m.save(self.root / "ci-bundle.json", self.bundle)
        compiler.publish(compiler.intent(1, "deny"), self.root / "approved.json")

    def test_committed_source_does_not_follow_dirty_worktree(self):
        before = m.source(self.revision)
        (self.root / "ci-repo/intent.json").write_text("{}")
        self.assertEqual(m.source(self.revision), before)
        with self.assertRaises(ValueError):
            m.verify(self.bundle)

    def test_actual_git_history_rejects_stale_bundle_without_publication(self):
        m.commit(compiler.intent(3, "deny"))
        result = m.rejected(m.promote)
        self.assertTrue(result["publication_unchanged"])
        self.assertEqual(
            compiler.state_read(self.root / "approved.json")["intent"]["application"],
            "deny",
        )

    def test_promotion_uses_exact_commit_and_does_not_rewrite_git(self):
        result = m.promote()
        self.assertEqual(result["commit"], self.revision)
        self.assertFalse(result["device_deployed"])
        self.assertEqual(m.head(), self.revision)
        self.assertEqual(
            compiler.state_read(self.root / "approved.json")["intent"]["application"],
            "allow",
        )

    def test_tampered_manifest_body_digest_source_and_tests_are_rejected(self):
        for field, value in [
            ("body", "permit ip any any"),
            ("body_sha256", "0" * 64),
            ("source_sha256", "1" * 64),
            ("tests_run", 7),
            ("intent", compiler.intent(3, "deny")),
        ]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.verify(dict(self.bundle, **{field: value}))

    def test_revision_is_literal_and_cannot_supply_git_options(self):
        for value in ("HEAD", "--help", self.revision + ":other", "f" * 39):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.source(value)

    def test_executable_intent_is_not_an_accepted_source_blob(self):
        m.git("update-index", "--chmod=+x", "intent.json")
        m.git("commit", "-m", "Invalid executable mode")
        with self.assertRaises(ValueError):
            m.source(m.head())

    def test_rollback_revalidates_historical_committed_bytes(self):
        m.promote()
        m.commit(compiler.intent(3, "deny"))
        m.save(
            self.root / "approved.json",
            compiler.publish(compiler.intent(3, "deny"), self.root / "other.json"),
        )
        result = m.promote(rollback=True)
        self.assertEqual(result["commit"], self.revision)
        self.assertEqual(result["application"], "allow")
        self.assertNotEqual(m.head(), self.revision)

    def test_invalid_snapshot_actually_fails_gate_test_suite(self):
        path = self.root / "ci-input.json"
        for value, expected in (
            (compiler.intent(), 0),
            (dict(compiler.intent(), administration="allow"), 1),
        ):
            path.write_text(json.dumps(value))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(m.gate(), expected)
            result = json.loads(output.getvalue())
            self.assertEqual(result["tests_run"], 8)
            self.assertEqual(result["passed"], expected == 0)

    def test_failed_child_gate_cannot_replace_bundle_or_publication(self):
        original = m.subprocess.run

        def execute(args, **kwargs):
            if args[0] == sys.executable:
                return subprocess.CompletedProcess(args, 1, '{"passed":false,"tests_run":8}', "")
            return original(args, **kwargs)

        before = {
            name: (self.root / name).read_bytes() for name in ("ci-bundle.json", "approved.json")
        }
        with (
            mock.patch.object(m.subprocess, "run", side_effect=execute),
            self.assertRaises(RuntimeError),
        ):
            m.rejected(m.build)
        self.assertTrue(
            all((self.root / name).read_bytes() == data for name, data in before.items())
        )

    def test_complete_gate_rejection_is_accepted_only_for_independently_invalid_source(
        self,
    ):
        original = m.subprocess.run

        def execute(args, **kwargs):
            if args[0] == sys.executable:
                return subprocess.CompletedProcess(
                    args,
                    1,
                    '{"passed":false,"tests_run":8,"errors":3,"failures":0}',
                    "",
                )
            return original(args, **kwargs)

        with mock.patch.object(m.subprocess, "run", side_effect=execute):
            with self.assertRaises(RuntimeError):
                m.rejected(m.build)
            m.commit(dict(compiler.intent(3, "deny"), administration="allow"))
            self.assertTrue(m.rejected(m.build)["publication_unchanged"])

    def test_malformed_gate_report_is_an_operational_error(self):
        original = m.subprocess.run

        def execute(args, **kwargs):
            if args[0] == sys.executable:
                return subprocess.CompletedProcess(args, 0, "not-json", "")
            return original(args, **kwargs)

        with (
            mock.patch.object(m.subprocess, "run", side_effect=execute),
            self.assertRaises(RuntimeError),
        ):
            m.rejected(m.build)

    def test_duplicate_and_oversize_intents_are_rejected(self):
        for raw in (b'{"version":1,"version":2}', b"x" * 4097):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                m.decode(raw)


if __name__ == "__main__":
    unittest.main()
