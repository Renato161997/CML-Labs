"""Durable teaching controller; changes only one real, isolated IOS XE route."""

import argparse
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from controller_contract import BAD, GOOD, MARKER, TOKEN, approvals, decode, validate

ROOT = Path("/lab")
PROC = Path("/proc")
HOST = "198.18.1.1"
PORT = 8080


class Problem(Exception):
    def __init__(self, status, code, job=None, exception_class=None):
        self.status, self.code, self.job = status, code, job
        self.exception_class = exception_class
        super().__init__(code)


class FixtureConfirmationFailure(Exception):
    """Explicit classroom fault after a real write and independent readback."""


class RestorationFailure(Exception):
    """A fresh device session could not verify compensation."""


def guarded(operation):
    try:
        return operation()
    except Problem:
        raise
    except Exception as error:
        raise Problem(503, "backend_unavailable", exception_class=type(error).__name__) from error


class Router:
    def __enter__(self):
        import requests
        from api_probe import connect_verified, connection_options
        from inventory_probe import collect

        with requests.Session() as http:
            http.trust_env = False
            self.facts = collect(http)
        assert self.facts["hostname"] == "API" and self.facts["ipv4"] == "198.18.0.1"
        self.session = connect_verified(connection_options())
        return self

    def __exit__(self, *error):
        self.session.close_session()

    def hops(self):
        from api_probe import hostname
        from route_probe import observed_next_hops

        assert hostname(self.session) == "API"
        return observed_next_hops(self.session)

    def set(self, hops):
        from route_probe import route_config

        if hops not in ([], [GOOD], [BAD]):
            raise ValueError("Unexpected rollback or desired next hop")
        payload = route_config("replace", hops[0]) if hops else route_config("delete")
        assert self.session.edit_config(target="running", config=payload).ok


class Controller:
    def __init__(self, database, approved, router=Router, fault=lambda: False):
        self.database, self.approved, self.router, self.fault = database, approved, router, fault
        self.lock = threading.Lock()
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    request_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
                    desired_state TEXT NOT NULL, status TEXT NOT NULL,
                    before_json TEXT, changed INTEGER, attempts INTEGER NOT NULL,
                    rollback_verified INTEGER, error_class TEXT, completed_seq INTEGER
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL REFERENCES jobs(request_id),
                    phase TEXT NOT NULL, attempt INTEGER NOT NULL, detail TEXT NOT NULL
                );
            """)
            db.commit()

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.database, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
        finally:
            db.close()

    @staticmethod
    def event(db, request_id, phase, attempt, detail):
        return db.execute(
            "INSERT INTO events(request_id,phase,attempt,detail) VALUES(?,?,?,?)",
            (request_id, phase, attempt, json.dumps(detail, sort_keys=True)),
        ).lastrowid

    @staticmethod
    def job(db, request_id):
        row = db.execute("SELECT * FROM jobs WHERE request_id=?", (request_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        before = result.pop("before_json")
        result["before_hops"] = decode(before) if before is not None else None
        for key in ("changed", "rollback_verified"):
            if result[key] is not None:
                result[key] = bool(result[key])
        return result

    def history(self):
        with self.lock, self.connection() as db:
            ids = [row[0] for row in db.execute("SELECT request_id FROM jobs ORDER BY rowid")]
            events = [
                {**dict(row), "detail": decode(row["detail"])}
                for row in db.execute("SELECT * FROM events ORDER BY seq")
            ]
            return {"jobs": [self.job(db, key) for key in ids], "events": events}

    def observed(self):
        with self.lock, self.connection() as db:
            row = db.execute(
                "SELECT desired_state FROM jobs WHERE status='succeeded' ORDER BY completed_seq DESC LIMIT 1"
            ).fetchone()
            desired = [GOOD] if row and row[0] == "present" else []
            with self.router() as device:
                actual, facts = device.hops(), device.facts
            network = ipaddress.IPv4Interface(facts["ipv4"] + "/" + facts["mask"]).network
            return {
                "facts": facts,
                "configured_next_hops": actual,
                "desired_next_hops": desired,
                "drift": actual != desired,
                "off_link_next_hops": [
                    hop for hop in actual if ipaddress.IPv4Address(hop) not in network
                ],
            }

    def restore(self, before):
        try:
            with self.router() as device:
                if device.hops() != before:
                    device.set(before)
                assert device.hops() == before
        except Exception as error:
            raise RestorationFailure() from error

    def apply(self, payload):
        value = validate(payload)
        key = value["request_id"]
        digest = hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self.lock, self.connection() as db:
            previous = self.job(db, key)
            if previous and previous["payload_hash"] != digest:
                raise Problem(409, "request_id_conflict")
            allowed = [validate(item) for item in self.approved()]
            if value not in allowed:
                raise Problem(403, "intent_not_approved")
            if previous and previous["status"] == "succeeded":
                return {"job": previous, "replayed": True, "applied_now": False}
            attempt = (previous["attempts"] if previous else 0) + 1
            db.execute(
                "INSERT INTO jobs(request_id,payload_hash,desired_state,status,attempts) VALUES(?,?,?,'pending',?) ON CONFLICT(request_id) DO UPDATE SET status='pending',attempts=excluded.attempts,before_json=NULL,changed=NULL,rollback_verified=NULL,error_class=NULL,completed_seq=NULL",
                (key, digest, value["state"], attempt),
            )
            self.event(db, key, "pending", attempt, {})
            db.commit()
            before = None
            try:
                with self.router() as device:
                    before = device.hops()
                    if before not in ([], [GOOD], [BAD]):
                        before = None
                        raise ValueError("Observed route exceeds the reversible fixture scope")
                    desired = [GOOD] if value["state"] == "present" else []
                    changed = before != desired
                    db.execute(
                        "UPDATE jobs SET before_json=?,changed=? WHERE request_id=?",
                        (json.dumps(before), changed, key),
                    )
                    self.event(db, key, "observed_before", attempt, {"hops": before})
                    db.commit()
                    if changed:
                        device.set(desired)
                    assert device.hops() == desired
                    self.event(db, key, "device_confirmed", attempt, {"hops": desired})
                    db.commit()
                    if self.fault():
                        raise FixtureConfirmationFailure()
                seq = self.event(db, key, "committed", attempt, {"changed": changed})
                db.execute(
                    "UPDATE jobs SET status='succeeded',completed_seq=? WHERE request_id=?",
                    (seq, key),
                )
                db.commit()
                return {"job": self.job(db, key), "replayed": False, "applied_now": changed}
            except Exception as error:
                rollback = None
                if before is not None:
                    rollback = False
                    try:
                        self.restore(before)
                        rollback = True
                    except RestorationFailure:
                        rollback = False
                self.event(
                    db,
                    key,
                    "failed",
                    attempt,
                    {"error_class": type(error).__name__, "rollback_verified": rollback},
                )
                db.execute(
                    "UPDATE jobs SET status='failed',rollback_verified=?,error_class=? WHERE request_id=?",
                    (rollback, type(error).__name__, key),
                )
                db.commit()
                raise Problem(502, "operation_failed", self.job(db, key)) from error


def make_server(address, controller):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *args):
            pass

        def reply(self, status, value):
            raw = json.dumps(value, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            fields = self.headers.get_all("Authorization", [])
            try:
                return len(fields) == 1 and hmac.compare_digest(
                    fields[0].encode("ascii"), ("Bearer " + TOKEN).encode("ascii")
                )
            except UnicodeError:
                return False

        def dispatch(self):
            if not self.authorized():
                return self.reply(401, {"error": "authentication_required"})
            try:
                if self.command == "GET":
                    if self.path == "/health":
                        result = {"kind": "service", "pid": os.getpid(), "marker": MARKER}
                    elif self.path == "/v1/device":
                        result = guarded(controller.observed)
                    elif self.path == "/v1/history":
                        result = guarded(controller.history)
                    else:
                        raise Problem(404, "unknown_resource")
                elif self.path == "/v1/route-intents":
                    lengths = self.headers.get_all("Content-Length", [])
                    if (
                        self.headers.get("Transfer-Encoding")
                        or len(lengths) != 1
                        or not lengths[0].isdigit()
                    ):
                        raise Problem(400, "invalid_body_framing")
                    length = int(lengths[0])
                    if not 0 < length <= 4096:
                        raise Problem(413, "body_limit")
                    if self.headers.get_all("Content-Type", []) != ["application/json"]:
                        raise Problem(415, "json_required")
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise Problem(400, "incomplete_body")
                    payload = validate(decode(raw))
                    result = guarded(lambda: controller.apply(payload))
                else:
                    raise Problem(404, "unknown_resource")
                self.reply(200, result)
            except Problem as error:
                self.reply(
                    error.status,
                    {
                        "error": error.code,
                        **({"job": error.job} if error.job else {}),
                        **(
                            {"exception_class": error.exception_class}
                            if error.exception_class
                            else {}
                        ),
                    },
                )
            except (ValueError, UnicodeError):
                self.reply(
                    422 if self.command == "POST" else 503,
                    {
                        "error": "invalid_intent"
                        if self.command == "POST"
                        else "backend_unavailable"
                    },
                )

        do_GET = dispatch
        do_POST = dispatch

    return ThreadingHTTPServer(address, Handler)


def owned(pid):
    if type(pid) is not int or pid <= 1:
        raise ValueError("Unsafe service PID")
    try:
        args = (PROC / str(pid) / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    except FileNotFoundError:
        return False
    return args == [os.fsencode(sys.executable), os.fsencode(Path(__file__).resolve()), b"serve"]


def health():
    connection = http.client.HTTPConnection(HOST, PORT, timeout=2)
    try:
        connection.request("GET", "/health", headers={"Authorization": "Bearer " + TOKEN})
        response = connection.getresponse()
        value = decode(response.read(4096))
        assert response.status == 200 and value["marker"] == MARKER
        return value
    finally:
        connection.close()


def stop():
    path = ROOT / "controller.pid"
    if not path.exists():
        return {"stopped": True}
    pid = int(path.read_text())
    if owned(pid):
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 5
        while owned(pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not owned(pid), "Owned controller did not stop"
    path.unlink(missing_ok=True)
    return {"stopped": True}


def start():
    path = ROOT / "controller.pid"
    if path.exists() and owned(int(path.read_text())):
        assert health()["pid"] == int(path.read_text())
        return {"started": True}
    with (ROOT / "controller.log").open("ab") as output:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "serve"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            start_new_session=True,
        )
    path.write_text(str(process.pid))
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        assert process.poll() is None, "Owned controller exited during startup"
        try:
            assert owned(process.pid) and health()["pid"] == process.pid
            return {"started": True}
        except (OSError, AssertionError):
            time.sleep(0.2)
    raise TimeoutError("Owned controller listener did not become ready")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("init", "serve", "start", "stop", "fault-on", "fault-off")
    )
    args = parser.parse_args()
    if os.geteuid() != 0 or (ROOT / "CML-CONTROLLER-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only a marked disposable controller guest may run this command")
    policy, fault = ROOT / "controller-approvals.json", ROOT / "controller-confirmation-fault"
    if args.action == "init":
        if not policy.exists():
            policy.write_text(json.dumps(approvals(), sort_keys=True))
            policy.chmod(0o600)
        assert decode(policy.read_text()) == approvals()
        result = {"initialized": True}
    elif args.action == "serve":
        app = Controller(
            ROOT / "controller.sqlite3", lambda: decode(policy.read_text()), fault=fault.exists
        )
        with make_server((HOST, PORT), app) as server:
            server.serve_forever()
        return
    elif args.action in ("fault-on", "fault-off"):
        fault.touch() if args.action == "fault-on" else fault.unlink(missing_ok=True)
        result = {"fault_enabled": fault.exists()}
    else:
        result = start() if args.action == "start" else stop()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
