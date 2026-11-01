"""Bounded policy validation, publication immutability and actual HTTP artifact tests."""

import copy
import http.client
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "policy_code", Path(__file__).resolve().parents[1] / "examples/security/policy_code.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PolicyCompilerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "approved.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_bounded_versions_compile_distinct_application_outcomes(self):
        permitted = m.compile_policy(m.intent())
        blocked = m.compile_policy(m.intent(2, "deny"))
        self.assertIn(" 10 permit tcp host 198.18.10.10 host 198.18.20.20 eq 8080\n", permitted)
        self.assertIn(" 10 deny tcp host 198.18.10.10 host 198.18.20.20 eq 8080\n", blocked)
        self.assertNotEqual(m.digest(permitted), m.digest(blocked))
        for config in (permitted, blocked):
            self.assertNotIn("permit ip any any", config)
            self.assertNotIn(" no 5\n", config)
            self.assertIn(" 20 deny tcp any host 198.18.20.20 eq 9090\n", config)
            self.assertIn(" no 10\n 10 ", config)

    def test_unsafe_candidates_leave_published_bytes_unchanged(self):
        m.publish(m.intent(), self.path)
        before = self.path.read_bytes()
        result = m.refuse_unsafe(self.path)
        self.assertEqual(result["unsafe_candidates_rejected"], 5)
        self.assertEqual(self.path.read_bytes(), before)

    def test_wrong_types_and_out_of_scope_values_rejected_before_publication(self):
        m.publish(m.intent(), self.path)
        before = self.path.read_bytes()
        for key, value in [
            ("version", True),
            ("version", 0),
            ("version", 101),
            ("version", "1"),
            ("source", "198.18.10.0/24"),
            ("target", "198.18.20.21/32"),
            ("application", "allow\npermit ip any any"),
            ("administration", "allow"),
            ("icmp", "deny"),
            ("application", []),
        ]:
            with self.subTest(key=key, value=value):
                candidate = dict(m.intent(), **{key: value})
                with self.assertRaises(ValueError):
                    m.publish(candidate, self.path)
                self.assertEqual(self.path.read_bytes(), before)

    def test_unknown_fields_and_non_objects_rejected(self):
        for candidate in (None, [], True, dict(m.intent(), commands=["anything"])):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                m.compile_policy(candidate)

    def test_unmodified_snapshot_restores_exact_original_body_and_digest(self):
        first = m.publish(m.intent(), self.path)
        snapshot = copy.deepcopy(m.state_read(self.path))
        changed = m.publish(m.intent(2, "deny"), self.path)
        self.assertNotEqual(first["sha256"], changed["sha256"])
        restored = m.publish(snapshot["intent"], self.path)
        self.assertEqual(restored, first)

    def test_body_or_hash_or_intent_corruption_rejected(self):
        original = m.publish(m.intent(), self.path)
        for key, value in [
            ("body", original["body"] + "permit ip any any\n"),
            ("sha256", "0" * 64),
            ("intent", m.intent(2, "deny")),
        ]:
            with self.subTest(key=key):
                modified = copy.deepcopy(original)
                modified[key] = value
                self.path.write_text(json.dumps(modified))
                with self.assertRaises(ValueError):
                    m.state_read(self.path)

    def test_failed_validation_does_not_create_artifact(self):
        with self.assertRaises(ValueError):
            m.publish(dict(m.intent(), administration="allow"), self.path)
        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.with_suffix(".next").exists())


class ArtifactHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = mock.patch.object(m, "ROOT", self.root)
        self.patch.start()
        self.path = self.root / "approved.json"
        self.first = m.publish(m.intent(), self.path)
        self.server = m.make_server(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.patch.stop()
        self.temp.cleanup()

    def get(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.request("GET", path)
            r = connection.getresponse()
            return r.status, r.getheader("ETag"), r.read()
        finally:
            connection.close()

    def test_actual_http_body_and_digest_track_only_accepted_publication(self):
        status, etag, body = self.get("/approved")
        self.assertEqual(status, 200)
        self.assertEqual(etag, '"' + m.digest(body.decode()) + '"')
        self.assertEqual(body.decode(), self.first["body"])
        m.refuse_unsafe(self.path)
        self.assertEqual(self.get("/approved"), (status, etag, body))
        changed = m.publish(m.intent(2, "deny"), self.path)
        after = self.get("/approved")
        self.assertNotEqual(after[1], etag)
        self.assertEqual(after[2].decode(), changed["body"])

    def test_corrupted_publication_is_unavailable_and_unknown_resource_is404(self):
        self.path.write_text("{}")
        self.assertEqual(self.get("/approved")[0], 503)
        self.assertEqual(self.get("/other")[0], 404)


if __name__ == "__main__":
    unittest.main()
