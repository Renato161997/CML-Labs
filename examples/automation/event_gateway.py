"""Signed fixture events delegate only approved, fixed-scope real device intents."""

import argparse
import hashlib
import hmac
import http.client
import http.server
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

from controller_contract import decode, intent

ROOT = Path("/lab")
MARKER = "CML-EVENT-GATEWAY-V1"
HOST, PORT = "198.18.1.1", 8081
SIGNING_KEY = b"Cml-Event-Signing-Only-983"  # Public teaching fixture, not an issued secret.
FIELDS = {"event_id", "timestamp", "operation", "device", "prefix"}
EVENTS = {"quarantine": ("withdraw-1", "absent"), "release": ("repair-1", "present")}


class Rejected(Exception):
    def __init__(self, status, error):
        super().__init__(error)
        self.status, self.error = status, error


def sign(raw, key=SIGNING_KEY):
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


def event(operation, now=None):
    identifier, _ = EVENTS[operation]
    return {
        "event_id": identifier,
        "timestamp": int(time.time()) if now is None else now,
        "operation": operation,
        "device": "API",
        "prefix": "192.0.2.42/32",
    }


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validated(raw, signature, now=None):
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= 2048:
        raise Rejected(400, "invalid_body_size")
    if (
        not isinstance(signature, str)
        or not re.fullmatch("[0-9a-f]{64}", signature)
        or not hmac.compare_digest(sign(raw), signature)
    ):
        raise Rejected(401, "invalid_signature")
    try:
        value = decode(raw.decode("utf-8"))
    except (ValueError, UnicodeError, TypeError) as error:
        raise Rejected(422, "invalid_event") from error
    if (
        not isinstance(value, dict)
        or set(value) != FIELDS
        or type(value["timestamp"]) is not int
        or any(type(value[k]) is not str for k in FIELDS - {"timestamp"})
    ):
        raise Rejected(422, "invalid_event")
    clock = int(time.time()) if now is None else now
    if abs(value["timestamp"] - clock) > 60:
        raise Rejected(422, "stale_event")
    if value["operation"] not in EVENTS:
        raise Rejected(422, "event_outside_scope")
    identifier, state = EVENTS[value["operation"]]
    if (value["event_id"], value["device"], value["prefix"]) != (
        identifier,
        "API",
        "192.0.2.42/32",
    ):
        raise Rejected(422, "event_outside_scope")
    return intent(identifier, state)


def device_forward(method, path, payload):
    # client.py is the registered guest name of controller_client.py.
    from client import request

    return request(method, path, payload)


def make_server(address, forward=device_forward, clock=time.time):
    class Handler(http.server.BaseHTTPRequestHandler):
        def reply(self, status, value):
            body = encode(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path != "/health":
                self.reply(404, {"error": "not_found"})
                return
            self.reply(200, {"marker": MARKER, "pid": os.getpid()})

        def do_POST(self):
            if self.path != "/events":
                self.reply(404, {"error": "not_found"})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if (
                self.headers.get("Transfer-Encoding") is not None
                or self.headers.get_all("Content-Type", []) != ["application/json"]
                or len(lengths) != 1
                or not re.fullmatch("[1-9][0-9]{0,3}", lengths[0])
                or not 1 <= int(lengths[0]) <= 2048
            ):
                self.reply(400, {"error": "invalid_framing"})
                return
            self.connection.settimeout(5)
            try:
                raw = self.rfile.read(int(lengths[0]))
            except TimeoutError:
                self.reply(408, {"error": "body_timeout"})
                return
            if len(raw) != int(lengths[0]):
                self.reply(400, {"error": "incomplete_body"})
                return
            signatures = self.headers.get_all("X-CML-Signature", [])
            signature = signatures[0] if len(signatures) == 1 else None
            try:
                payload = validated(raw, signature, now=int(clock()))
            except Rejected as error:
                self.reply(error.status, {"error": error.error})
                return
            try:
                status, value = forward("POST", "/v1/route-intents", payload)
            except (OSError, http.client.HTTPException):
                self.reply(503, {"error": "controller_unavailable"})
                return
            self.reply(status, value)

        def method_rejected(self):
            self.reply(405, {"error": "method_not_allowed"})

        do_PUT = method_rejected
        do_PATCH = method_rejected
        do_DELETE = method_rejected

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(address, Handler)
    server.daemon_threads = True
    return server


def process():
    p = ROOT / "event-gateway.pid"
    if p.is_symlink():
        raise PermissionError("Foreign PID link refused")
    if not p.exists():
        return None
    meta = p.lstat()
    assert stat.S_ISREG(meta.st_mode) and meta.st_uid == 0 and meta.st_nlink == 1
    pid = int(p.read_text())
    assert pid > 1
    proc = Path("/proc") / str(pid)
    if not proc.exists():
        return None
    if (proc / "stat").read_text().split(") ", 1)[1].startswith("Z "):
        return None
    args = (proc / "cmdline").read_bytes().split(b"\0")
    assert (
        len(args) >= 3 and args[1] == str(Path(__file__).resolve()).encode() and args[2] == b"serve"
    )
    return pid


def start():
    assert process() is None
    log = ROOT / "event-gateway.log"
    assert not log.is_symlink()
    with log.open("ab") as output:
        log.chmod(0o600)
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "serve"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    p = ROOT / "event-gateway.pid"
    p.write_text(str(child.pid))
    p.chmod(0o600)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection(HOST, PORT, timeout=1)
            try:
                conn.request("GET", "/health")
                res = conn.getresponse()
                body = decode(res.read(1024))
                if res.status == 200 and body == {"marker": MARKER, "pid": child.pid}:
                    return {"status": "passed", "gateway_started": True}
            finally:
                conn.close()
        except OSError:
            time.sleep(0.2)
    raise TimeoutError("Owned event gateway did not become healthy")


def stop():
    pid = process()
    assert pid is not None
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 8
    while process() is not None and time.monotonic() < deadline:
        time.sleep(0.1)
    assert process() is None
    return {"status": "passed", "gateway_stopped": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "serve", "approval-off", "approval-on"])
    args = parser.parse_args()
    if os.geteuid() != 0 or (ROOT / "CML-EVENT-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the marked disposable event fixture is accepted")
    if args.action == "serve":
        with make_server((HOST, PORT)) as server:
            server.serve_forever(poll_interval=0.1)
        return
    if args.action.startswith("approval-"):
        from api_security import policy

        value = policy(args.action == "approval-on")
    else:
        value = start() if args.action == "start" else stop()
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
