"""Offline webhook/intent teaching service. Validates requests; never changes devices."""

import argparse
import hmac
import json
import os
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 8192
INTERFACES = {"GigabitEthernet0/0", "GigabitEthernet0/1", "Loopback0"}


def validate_intent(value):
    if not isinstance(value, dict) or set(value) != {"event_id", "device", "interface", "enabled"}:
        return False
    return (
        isinstance(value["event_id"], str)
        and 1 <= len(value["event_id"]) <= 64
        and value["device"] in ("R1", "R2")
        and isinstance(value["device"], str)
        and isinstance(value["interface"], str)
        and value["interface"] in INTERFACES
        and type(value["enabled"]) is bool
    )


def make_server(address, secret):
    if not secret:
        raise ValueError("Set LAB_WEBHOOK_SECRET; there is no default credential")
    seen = OrderedDict()
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Do not print headers, tokens or payloads.

        def reply(self, status, data):
            raw = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self.reply(
                200 if self.path == "/health" else 404,
                {"status": "ok"} if self.path == "/health" else {"error": "not-found"},
            )

        def do_POST(self):
            if self.path != "/events":
                self.reply(404, {"error": "not-found"})
                return
            if not hmac.compare_digest(
                self.headers.get("Authorization", "").encode("utf-8"),
                ("Bearer " + secret).encode("utf-8"),
            ):
                self.reply(401, {"error": "unauthorized"})
                return
            if self.headers.get_content_type() != "application/json":
                self.reply(415, {"error": "application-json-required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.reply(400, {"error": "invalid-length"})
                return
            if not 0 < length <= MAX_BODY or self.headers.get("Transfer-Encoding"):
                self.reply(413, {"error": "invalid-size"})
                return
            self.connection.settimeout(3)
            try:
                raw = self.rfile.read(length)
                value = json.loads(raw)
            except (ValueError, UnicodeError, TimeoutError, OSError):
                self.reply(400, {"error": "invalid-json"})
                return
            if not validate_intent(value):
                self.reply(422, {"error": "invalid-intent"})
                return
            with lock:
                key = value["event_id"]
                if key in seen:
                    if seen[key] != value:
                        self.reply(409, {"error": "event-id-conflict"})
                        return
                    self.reply(200, {"decision": "already-accepted", "applied": False})
                    return
                seen[key] = value
                if len(seen) > 1000:
                    seen.popitem(last=False)
            self.reply(202, {"decision": "accepted", "applied": False})

    server = ThreadingHTTPServer(address, Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()
    server = make_server((args.host, args.port), os.environ.get("LAB_WEBHOOK_SECRET"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
