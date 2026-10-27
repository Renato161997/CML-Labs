"""Inspectable HTTP/SQLite training service; bind only an isolated lab interface."""

import argparse
import json
import sqlite3
import threading
from collections import Counter
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class State:
    def __init__(self, database):
        self.database = str(database)
        self.lock = threading.RLock()
        self.mode = "healthy"
        self.revision = 1
        self.attempts = {}
        self.events = []
        self.counts = Counter()
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS events (key TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )


def handler_for(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body=None, headers=None):
            trace = self.headers.get("X-Request-ID", "")[:80]
            with state.lock:
                state.counts[str(code)] += 1
                state.events.append(
                    {
                        "trace": "" if state.mode == "no-trace" else trace,
                        "path": urlsplit(self.path).path,
                        "status": code,
                    }
                )
                state.events[:] = state.events[-512:]
            raw = b"" if body is None else json.dumps(body, sort_keys=True).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Request-ID", trace)
            for name, value in (headers or {}).items():
                self.send_header(name, str(value))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            with state.lock:
                mode, revision = state.mode, state.revision
            if parsed.path == "/health":
                return self.reply(200, {"status": "ok"})
            if parsed.path == "/items":
                try:
                    offset, limit = (
                        int(query.get("offset", ["0"])[0]),
                        int(query.get("limit", ["3"])[0]),
                    )
                    if offset < 0 or not 1 <= limit <= 5:
                        raise ValueError
                except ValueError:
                    return self.reply(400, {"error": "invalid pagination"})
                next_offset = offset + limit if offset + limit < 7 else None
                if mode == "cursor-loop" and next_offset is not None:
                    next_offset = offset
                return self.reply(
                    200,
                    {
                        "items": [{"id": i} for i in range(offset, min(offset + limit, 7))],
                        "next": next_offset,
                    },
                )
            if parsed.path.startswith("/resource/"):
                if mode == "unavailable":
                    return self.reply(503, {"error": "temporarily unavailable"})
                if parsed.path != "/resource/1":
                    return self.reply(404, {"error": "not found"})
                etag = '"v1"' if mode == "stale-etag" else f'"v{revision}"'
                headers = {"ETag": etag, "Cache-Control": "private, max-age=0, must-revalidate"}
                if self.headers.get("If-None-Match") == etag:
                    return self.reply(304, headers=headers)
                return self.reply(200, {"id": 1, "revision": revision}, headers)
            if parsed.path == "/throttle":
                key = query.get("key", [""])[0][:80]
                with state.lock:
                    state.attempts[key] = state.attempts.get(key, 0) + 1
                    attempt = state.attempts[key]
                if mode == "always-throttle" or attempt <= 2:
                    return self.reply(429, {"error": "rate limited"}, {"Retry-After": "1"})
                return self.reply(200, {"attempt": attempt})
            if parsed.path == "/events":
                with state.lock:
                    events = list(state.events)
                return self.reply(200, {"events": events})
            if parsed.path == "/metrics":
                with state.lock:
                    counts = dict(state.counts)
                return self.reply(200, {"requests": sum(counts.values()), "statuses": counts})
            if parsed.path.startswith("/records/"):
                with closing(sqlite3.connect(state.database)) as db, db:
                    row = db.execute(
                        "SELECT payload FROM events WHERE key=?", (parsed.path[9:],)
                    ).fetchone()
                return self.reply(
                    200 if row else 404,
                    {"payload": json.loads(row[0])} if row else {"error": "not found"},
                )
            return self.reply(404, {"error": "not found"})

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise TypeError
            except (TypeError, ValueError):
                return self.reply(400, {"error": "invalid JSON object"})
            if self.path == "/control":
                # Public training fixture, never a real credential or production API.
                if self.headers.get("X-Lab-Control") != "public-training-fixture":
                    return self.reply(403, {"error": "denied"})
                if body.get("mode") not in (
                    "healthy",
                    "cursor-loop",
                    "unavailable",
                    "stale-etag",
                    "always-throttle",
                    "no-trace",
                    "read-only",
                ):
                    return self.reply(400, {"error": "unknown mode"})
                with state.lock:
                    state.mode = body["mode"]
                    state.revision = 2 if state.mode == "stale-etag" else 1
                return self.reply(200, {"mode": state.mode})
            if self.path == "/revision":
                if self.headers.get("X-Lab-Control") != "public-training-fixture" or body.get(
                    "revision"
                ) not in (1, 2):
                    return self.reply(403, {"error": "denied"})
                with state.lock:
                    state.revision = body["revision"]
                return self.reply(200, {"revision": state.revision})
            if self.path == "/records":
                key = body.get("key")
                payload = body.get("payload")
                if (
                    not isinstance(key, str)
                    or not 1 <= len(key) <= 80
                    or not isinstance(payload, dict)
                ):
                    return self.reply(400, {"error": "invalid record"})
                encoded = json.dumps(payload, sort_keys=True)
                try:
                    with closing(sqlite3.connect(state.database, timeout=3)) as db, db:
                        if state.mode == "read-only":
                            db.execute("PRAGMA query_only=ON")
                        cursor = db.execute(
                            "INSERT OR IGNORE INTO events VALUES (?,?)", (key, encoded)
                        )
                        inserted = cursor.rowcount == 1
                        observed = db.execute(
                            "SELECT payload FROM events WHERE key=?", (key,)
                        ).fetchone()[0]
                    if observed != encoded:
                        return self.reply(409, {"error": "conflicting idempotency key"})
                    return self.reply(201 if inserted else 200, {"created": inserted})
                except sqlite3.OperationalError:
                    return self.reply(503, {"error": "storage unavailable"})
            return self.reply(404, {"error": "not found"})

    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", required=True)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--database", default="/lab/events.sqlite")
    args = parser.parse_args()
    ThreadingHTTPServer((args.bind, args.port), handler_for(State(args.database))).serve_forever()
