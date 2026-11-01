"""Real loopback HTTP checks and JSON Schema negative controls."""

import http.client
import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import ValidationError

spec = importlib.util.spec_from_file_location(
    "openapi_contract",
    Path(__file__).resolve().parents[1] / "examples/automation/openapi_contract.py",
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ContractSchemaTests(unittest.TestCase):
    def test_schema_requires_types_fields_and_no_extras(self):
        valid = {"id": 1, "name": "fixture-1", "interface": {"name": "eth1", "carrier": True}}
        m.schema_check(m.contract(), 200, valid)
        for body in (
            dict(valid, id=True),
            dict(valid, extra=True),
            dict(valid, interface={"name": "eth1", "carrier": "up"}),
            dict(valid, interface={"name": "eth1"}),
        ):
            with self.subTest(body=body), self.assertRaises(ValidationError):
                m.schema_check(m.contract(), 200, body)

    def test_unknown_status_or_external_reference_refused(self):
        with self.assertRaises(ValueError):
            m.schema_check(m.contract(), 201, {})
        document = m.contract()
        document["paths"]["/devices/{device_id}"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"] = "https://example.test/remote-schema"
        with self.assertRaises(ValueError):
            m.schema_check(document, 200, {})

    def test_json_duplicates_nonfinite_constants_and_oversize_refused(self):
        for raw in (b'{"id":1,"id":1}', b'{"id":NaN}', b" " * 32769):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                m.decoded(raw)

    def test_structurally_valid_false_carrier_is_not_a_truth_guarantee(self):
        body = {"id": 1, "name": "fixture-1", "interface": {"name": "eth1", "carrier": False}}
        m.schema_check(m.contract(), 200, body)


class ContractHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch_root = mock.patch.object(m, "ROOT", self.root)
        self.patch_root.start()
        (self.root / "api-mode").write_text("good")
        self.patch_facts = mock.patch.object(
            m,
            "facts",
            side_effect=lambda: {
                "id": 1,
                "name": "fixture-1",
                "interface": {"name": "eth1", "carrier": True},
            },
        )
        self.patch_facts.start()
        self.server = m.make_server(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        connection = http.client.HTTPConnection

        def redirected(host, port, timeout):
            self.assertEqual((host, port), (m.SERVER, 8080))
            return connection("127.0.0.1", self.server.server_port, timeout=timeout)

        self.patch_connection = mock.patch.object(m.http.client, "HTTPConnection", redirected)
        self.patch_connection.start()

    def tearDown(self):
        self.patch_connection.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.patch_facts.stop()
        self.patch_root.stop()
        self.temp.cleanup()

    def test_valid_document_and_actual_response_accepted(self):
        result = m.verify()
        self.assertTrue(result["accepted"])
        self.assertEqual(result["wire_status"], 200)
        self.assertTrue(result["body"]["interface"]["carrier"])

    def test_auth_parameter_resource_and_method_errors_are_observed(self):
        result = m.probe("auth-errors")
        self.assertEqual(result["documented_errors_validated"], 3)
        self.assertTrue(result["undocumented_method_rejected"])

    def test_actual_http_schema_status_media_and_document_faults(self):
        for mode, reason in (
            ("schema", "schema_violation"),
            ("status", "undocumented_status"),
            ("media", "unexpected_media"),
            ("contract", "document_changed"),
        ):
            with self.subTest(mode=mode):
                (self.root / "api-mode").write_text(mode)
                result = m.verify()
                self.assertFalse(result["accepted"])
                self.assertEqual(result["reason"], reason)
                (self.root / "api-mode").write_text("good")
                self.assertTrue(m.verify()["accepted"])

    def test_semantic_lie_remains_schema_valid_and_is_reported_as_limit(self):
        (self.root / "api-mode").write_text("lie")
        result = m.probe("semantic-lie")
        self.assertTrue(result["contract_accepted"])
        self.assertTrue(result["schema_only_does_not_prove_truth"])


if __name__ == "__main__":
    unittest.main()
