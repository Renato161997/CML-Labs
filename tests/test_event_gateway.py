import http.client
import importlib.util
import json
import socket
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / "examples/automation"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("event_gateway", SOURCE / "event_gateway.py")
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
sys.path.pop(0)
NOW = 1700000000


class SignedEventContract(unittest.TestCase):
    def checked(self, value):
        raw = gateway.encode(value)
        return gateway.validated(raw, gateway.sign(raw), NOW)

    def test_exact_declared_operations_map_to_fixed_intents(self):
        for op, request_id, state in [
            ("quarantine", "withdraw-1", "absent"),
            ("release", "repair-1", "present"),
        ]:
            value = self.checked(gateway.event(op, NOW))
            self.assertEqual(
                value,
                {
                    "request_id": request_id,
                    "device": "API",
                    "prefix": "192.0.2.42/32",
                    "next_hop": "198.18.0.2",
                    "state": state,
                },
            )

    def test_tampered_body_and_wrong_key_are_rejected(self):
        raw = gateway.encode(gateway.event("quarantine", NOW))
        for data, signature in [
            (raw + b" ", gateway.sign(raw)),
            (raw, gateway.sign(raw, b"wrong-public-fixture")),
        ]:
            with self.assertRaises(gateway.Rejected) as caught:
                gateway.validated(data, signature, NOW)
            self.assertEqual(caught.exception.status, 401)

    def test_missing_malformed_or_non_ascii_signature_is_rejected(self):
        raw = gateway.encode(gateway.event("quarantine", NOW))
        for signature in [None, "", "x" * 64, "é" * 64, b"a" * 64]:
            with self.subTest(signature=signature), self.assertRaises(gateway.Rejected) as caught:
                gateway.validated(raw, signature, NOW)
            self.assertEqual(caught.exception.status, 401)

    def test_expired_and_future_events_are_rejected(self):
        for timestamp in [NOW - 61, NOW + 61]:
            with self.subTest(timestamp=timestamp), self.assertRaises(gateway.Rejected) as caught:
                self.checked(gateway.event("quarantine", timestamp))
            self.assertEqual(caught.exception.error, "stale_event")
        for timestamp in [NOW - 60, NOW + 60]:
            self.assertEqual(
                self.checked(gateway.event("quarantine", timestamp))["state"], "absent"
            )

    def test_authenticated_data_cannot_expand_scope_or_approve_itself(self):
        good = gateway.event("quarantine", NOW)
        for key, value in [
            ("device", "OTHER"),
            ("prefix", "0.0.0.0/0"),
            ("event_id", "new-1"),
            ("operation", "shell"),
            ("approved", True),
            ("timestamp", True),
            ("timestamp", float(NOW)),
            ("operation", []),
            ("device", 1),
        ]:
            with self.subTest(key=key, value=value), self.assertRaises(gateway.Rejected) as caught:
                self.checked({**good, key: value})
            self.assertEqual(caught.exception.status, 422)

    def test_duplicate_fields_and_invalid_utf8_are_rejected(self):
        good = gateway.encode(gateway.event("quarantine", NOW))
        duplicate = good[:-1] + b',"device":"OTHER"}'
        for raw in [duplicate, b"\xff", b"null", b"[]"]:
            with self.subTest(raw=raw), self.assertRaises(gateway.Rejected) as caught:
                gateway.validated(raw, gateway.sign(raw), NOW)
            self.assertEqual(caught.exception.status, 422)

    def test_body_bounds_precede_decoding(self):
        for raw in [b"", b"x" * 2049, None, bytearray(b"x")]:
            with self.assertRaises(gateway.Rejected) as caught:
                gateway.validated(raw, "x" * 64, NOW)
            self.assertEqual(caught.exception.status, 400)


class GatewayHTTP(unittest.TestCase):
    def setUp(self):
        self.forward = Mock(return_value=(200, {"job": {"status": "succeeded"}, "replayed": False}))
        self.server = gateway.make_server(("127.0.0.1", 0), forward=self.forward, clock=lambda: NOW)
        self.thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def wire(
        self,
        raw=None,
        signature=None,
        extras=(),
        method="POST",
        path="/events",
        replace=(),
        half_close=False,
    ):
        if raw is None:
            raw = gateway.encode(gateway.event("quarantine", NOW))
        if signature is None:
            signature = gateway.sign(raw)
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(raw))),
            ("X-CML-Signature", signature),
        ]
        for key, value in replace:
            headers = [(k, v) for k, v in headers if k.lower() != key.lower()]
            headers.append((key, value))
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        try:
            conn.putrequest(method, path)
            for key, value in [*headers, *extras]:
                conn.putheader(key, value)
            conn.endheaders(raw)
            if half_close:
                conn.sock.shutdown(socket.SHUT_WR)
            response = conn.getresponse()
            self.assertEqual(response.getheader("Content-Type"), "application/json")
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def test_real_http_delegates_only_the_validated_intent(self):
        self.assertEqual(self.wire()[0], 200)
        self.forward.assert_called_once_with(
            "POST", "/v1/route-intents", gateway.intent("withdraw-1", "absent")
        )

    def test_bad_signature_never_reaches_controller(self):
        self.assertEqual(self.wire(signature="0" * 64), (401, {"error": "invalid_signature"}))
        self.forward.assert_not_called()

    def test_root_approval_denial_is_not_turned_into_success(self):
        self.forward.return_value = 403, {"error": "intent_not_approved"}
        self.assertEqual(self.wire(), (403, {"error": "intent_not_approved"}))

    def test_failed_controller_never_fabricates_success(self):
        self.forward.side_effect = ConnectionRefusedError()
        self.assertEqual(self.wire(), (503, {"error": "controller_unavailable"}))

    def test_ambiguous_length_or_type_is_rejected_without_delegation(self):
        for key, value in [
            ("Content-Length", "1"),
            ("Content-Type", "application/json"),
            ("Transfer-Encoding", "chunked"),
        ]:
            with self.subTest(key=key):
                self.assertEqual(self.wire(extras=[(key, value)])[0], 400)
        self.forward.assert_not_called()

    def test_duplicate_signature_is_rejected_without_delegation(self):
        self.assertEqual(self.wire(extras=[("X-CML-Signature", "0" * 64)])[0], 401)
        self.forward.assert_not_called()

    def test_non_json_or_oversized_frame_is_rejected(self):
        for replacement in [
            [("Content-Type", "text/plain")],
            [("Content-Length", "4097")],
            [("Content-Length", "0")],
        ]:
            self.assertEqual(self.wire(replace=replacement)[0], 400)
        self.forward.assert_not_called()

    def test_wrong_resources_and_mutating_methods_cannot_delegate(self):
        self.assertEqual(self.wire(path="/events/")[0], 404)
        self.assertEqual(self.wire(method="PUT")[0], 405)
        self.assertEqual(self.wire(method="DELETE")[0], 405)
        self.forward.assert_not_called()

    def test_incomplete_body_never_delegates_even_with_a_valid_signature(self):
        raw = gateway.encode(gateway.event("quarantine", NOW))
        self.assertEqual(
            self.wire(raw=raw, replace=[("Content-Length", str(len(raw) + 1))], half_close=True),
            (400, {"error": "incomplete_body"}),
        )
        self.forward.assert_not_called()

    def test_health_reports_real_local_pid_without_delegation(self):
        status, value = self.wire(method="GET", path="/health")
        self.assertEqual(status, 200)
        self.assertEqual(value["marker"], gateway.MARKER)
        self.assertGreater(value["pid"], 1)
        self.forward.assert_not_called()


if __name__ == "__main__":
    unittest.main()
