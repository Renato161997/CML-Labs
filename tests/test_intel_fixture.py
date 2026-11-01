"""Host logic plus actual loopback conditional-HTTP tests; no live intelligence."""

import copy
import importlib.util
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "intel_fixture", Path(__file__).resolve().parents[1] / "examples/security/intel_fixture.py"
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class IndicatorProfileTests(unittest.TestCase):
    def setUp(self):
        self.anchor = int(time.time())
        self.value = m.bundle(self.anchor)

    def test_active_indicator_only_and_inactive_controls(self):
        records = m.parsed(m.encoded(self.value))
        self.assertEqual(
            m.matches(records, m.TARGET, self.anchor), [self.value["objects"][0]["id"]]
        )
        for suffix in range(11, 15):
            self.assertEqual(m.matches(records, "198.18.10." + str(suffix), self.anchor), [])

    def test_validity_has_inclusive_start_and_exclusive_end(self):
        record = m.parsed(m.encoded(self.value))[0]
        self.assertEqual(len(m.matches([record], m.TARGET, record["from"])), 1)
        self.assertEqual(m.matches([record], m.TARGET, record["until"]), [])

    def test_unspecified_confidence_is_not_zero_or_high_confidence(self):
        del self.value["objects"][0]["confidence"]
        record = m.parsed(m.encoded(self.value))[0]
        self.assertIsNone(record["confidence"])
        self.assertEqual(m.matches([record], m.TARGET, self.anchor), [])
        for invalid in (True, 101, -1, None, 85.0, "85"):
            with self.subTest(invalid=invalid):
                self.value["objects"][0]["confidence"] = invalid
                with self.assertRaises((ValueError, TypeError)):
                    m.parsed(m.encoded(self.value))

    def test_unbounded_validity_is_supported_but_revocation_excludes(self):
        del self.value["objects"][0]["valid_until"]
        records = m.parsed(m.encoded(self.value))
        self.assertEqual(len(m.matches(records, m.TARGET, self.anchor + 7200)), 1)
        self.value["objects"][0]["revoked"] = True
        self.assertEqual(m.matches(m.parsed(m.encoded(self.value)), m.TARGET, self.anchor), [])

    def test_invalid_scalar_pattern_version_window_and_schema_rejected(self):
        for key, value in [
            ("revoked", "false"),
            ("pattern", "[domain-name:value = 'example.test']"),
            ("pattern", "[ipv4-addr:value = '8.8.8.8']"),
            ("pattern_version", "2.0"),
            ("valid_until", m.stamp(self.anchor - 3600)),
            ("modified", m.stamp(self.anchor - 9000)),
            ("name", []),
            ("unknown", True),
        ]:
            with self.subTest(key=key, value=value):
                item = copy.deepcopy(self.value)
                item["objects"][0][key] = value
                with self.assertRaises((ValueError, TypeError)):
                    m.parsed(m.encoded(item))

    def test_duplicate_fields_and_object_versions_rejected(self):
        raw = m.encoded(self.value).replace(
            b'"confidence":85', b'"confidence":85,"confidence":85', 1
        )
        with self.assertRaises((ValueError, TypeError)):
            m.parsed(raw)
        self.value["objects"].append(copy.deepcopy(self.value["objects"][0]))
        with self.assertRaises((ValueError, TypeError)):
            m.parsed(m.encoded(self.value))

    def test_payload_and_object_count_bounded(self):
        with self.assertRaises((ValueError, TypeError)):
            m.parsed(b" " * 65537)
        self.value["objects"] = self.value["objects"] * 7
        with self.assertRaises((ValueError, TypeError)):
            m.parsed(m.encoded(self.value))


class ConditionalHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch_root = mock.patch.object(m, "ROOT", self.root)
        self.patch_root.start()
        (self.root / "intel-mode").write_text("healthy")
        (self.root / "intel-anchor").write_text(str(int(time.time())))
        self.server = m.make_server(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        original = m.http.client.HTTPConnection

        def connection(host, port, timeout):
            self.assertEqual((host, port), (m.SOURCE, 8080))
            return original("127.0.0.1", self.server.server_port, timeout=timeout)

        self.patch_connection = mock.patch.object(m.http.client, "HTTPConnection", connection)
        self.patch_connection.start()
        self.cache = self.root / "intel-cache.json"

    def tearDown(self):
        self.patch_connection.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.patch_root.stop()
        self.temp.cleanup()

    def test_real_http_full_teaching_sequence_and_final_revoked_cache(self):
        self.assertEqual(m.probe("baseline")["verdict"], "matched")
        self.assertEqual(m.probe("cached")["wire_status"], 304)
        (self.root / "intel-mode").write_text("unavailable")
        self.assertEqual(m.probe("offline")["verdict"], "unknown")
        (self.root / "intel-mode").write_text("healthy")
        m.probe("recovered")
        (self.root / "intel-mode").write_text("malformed")
        self.assertEqual(m.probe("invalid-feed")["verdict"], "unknown")
        (self.root / "intel-mode").write_text("healthy")
        m.probe("recovered")
        (self.root / "intel-mode").write_text("withdrawn")
        self.assertEqual(m.probe("withdrawn")["verdict"], "no-match-not-benign")
        self.assertTrue(m.probe("corrupt-cache")["cache_corruption_detected"])
        final = m.probe("cached-withdrawn")
        self.assertEqual((final["matching_indicators"], final["wire_status"]), (0, 304))

    def test_actual_initial200_and_conditional304(self):
        first = m.fetch(self.cache)
        second = m.fetch(self.cache)
        self.assertEqual((first["verified"], first["wire_status"]), (True, 200))
        self.assertEqual((second["verified"], second["wire_status"]), (True, 304))
        self.assertEqual(first["records"], second["records"])

    def test_real503_is_unknown_and_does_not_promote_cached_indicators(self):
        self.assertTrue(m.fetch(self.cache)["verified"])
        before = self.cache.read_bytes()
        (self.root / "intel-mode").write_text("unavailable")
        result = m.fetch(self.cache)
        self.assertEqual(
            (result["verified"], result["wire_status"], result["records"]), (False, 503, [])
        )
        self.assertEqual(before, self.cache.read_bytes())
        (self.root / "intel-mode").write_text("healthy")
        self.assertEqual(m.fetch(self.cache)["wire_status"], 304)

    def test_invalid_indicator_on_real200_is_unknown_and_preserves_cache(self):
        m.fetch(self.cache)
        before = self.cache.read_bytes()
        (self.root / "intel-mode").write_text("malformed")
        result = m.fetch(self.cache)
        self.assertEqual(
            (result["verified"], result["wire_status"], result["records"]), (False, 200, [])
        )
        self.assertEqual(before, self.cache.read_bytes())

    def test_revocation_changes_etag_and_live_verdict(self):
        first = m.fetch(self.cache)
        before = json.loads(self.cache.read_text())["etag"]
        self.assertEqual(len(m.matches(first["records"], m.TARGET, time.time())), 1)
        (self.root / "intel-mode").write_text("withdrawn")
        second = m.fetch(self.cache)
        self.assertEqual(second["wire_status"], 200)
        self.assertNotEqual(before, json.loads(self.cache.read_text())["etag"])
        self.assertEqual(m.matches(second["records"], m.TARGET, time.time()), [])

    def test_corrupted_cached_bytes_force_actual200_revalidation(self):
        m.fetch(self.cache)
        cached = json.loads(self.cache.read_text())
        cached["body"] += " "
        self.cache.write_text(json.dumps(cached))
        result = m.fetch(self.cache)
        self.assertTrue(result["verified"])
        self.assertTrue(result["cache_corruption_detected"])
        self.assertEqual(result["wire_status"], 200)
        self.assertFalse(m.cache_load(self.cache)[1])


if __name__ == "__main__":
    unittest.main()
