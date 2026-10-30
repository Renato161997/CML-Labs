"""Actual HTTP packet, peer-identity and bounded-probe checks for firewall labs."""

import http.server
import importlib.util
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "traffic_fixture", ROOT / "examples/security/traffic_fixture.py"
)
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


class TrafficFixtureTests(unittest.TestCase):
    def test_real_server_reports_observed_peer_and_label(self):
        server = fixture.server("127.0.0.1", 0, "OUTSIDE")
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        thread.start()
        try:
            self.assertEqual(
                fixture.probe("127.0.0.1", server.server_address[1]),
                {
                    "reachable": True,
                    "status": 200,
                    "peer": "127.0.0.1",
                    "server": "OUTSIDE",
                },
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_unapproved_addresses_never_open_a_connection(self):
        with patch.object(fixture.http.client, "HTTPConnection") as connect:
            for value in (
                "1.1.1.1",
                "192.168.1.1",
                "169.254.169.254",
                "::1",
                "example.com",
            ):
                with self.subTest(address=value), self.assertRaises(ValueError):
                    fixture.probe(value)
            connect.assert_not_called()

    def test_nonresponsive_http_peer_is_a_bounded_negative_observation(self):
        class SlowHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                time.sleep(0.15)

            def log_message(self, *_args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        thread.start()
        try:
            self.assertEqual(
                fixture.probe("127.0.0.1", server.server_address[1], timeout=0.03),
                {"reachable": False, "reason": "timeout"},
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
