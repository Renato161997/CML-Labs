"""Isolated OAuth2/PKCE teaching subset. Fixed synthetic consent/user; not an IdP.

Plain HTTP is restricted to loopback or198.18/15 in client tooling; use only an
isolated CML link. No real account, production token or TLS claim. Protocol
references: RFC6749, RFC7636, RFC9700. Opaque credentials are never logged and
SQLite stores their hashes. The server has one deliberately public fixture
client and exact callback, not production registration/authentication.
The deliberately public /control fixture injects named insecure policies only
for isolated fault/recovery experiments; this code must not serve real users.
"""

import argparse
import base64
import hashlib
import hmac
import http.server
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CLIENT = "cml-public-client"
CALLBACK = "http://198.18.0.2/callback"
SCOPE = "inventory:read"
VERIFIER = re.compile(r"[A-Za-z0-9._~-]{43,128}\Z")


def isolated_address(value):
    ip = ipaddress.ip_address(value)
    if ip.version != 4 or not (ip.is_loopback or ip in ipaddress.ip_network("198.18.0.0/15")):
        raise ValueError("not an isolated fixture address")
    return ip


def digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def challenge(value):
    if not isinstance(value, str) or not VERIFIER.fullmatch(value):
        raise ValueError("invalid verifier")
    return (
        base64.urlsafe_b64encode(hashlib.sha256(value.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )


def parameters(raw):
    pairs = urllib.parse.parse_qsl(
        raw, keep_blank_values=True, max_num_fields=16, strict_parsing=True
    )
    if len({k for k, v in pairs}) != len(pairs):
        raise ValueError("duplicate parameter")
    return dict(pairs)


class Store:
    def __init__(self, path, clock=time.time, access_ttl=3):
        self.mode = "healthy"
        self.clock = clock
        self.ttl = access_ttl
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS families(id TEXT PRIMARY KEY,revoked INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS codes(hash TEXT PRIMARY KEY,challenge TEXT NOT NULL,expires REAL NOT NULL,used INTEGER NOT NULL,family TEXT); CREATE TABLE IF NOT EXISTS tokens(hash TEXT PRIMARY KEY,kind TEXT NOT NULL,family TEXT NOT NULL,expires REAL NOT NULL,used INTEGER NOT NULL);"
        )
        if str(path) != ":memory:":
            os.chmod(path, 0o600)

    def issue_code(self, p):
        if p.get("client_id") != CLIENT or p.get("redirect_uri") != CALLBACK:
            return 400, {"error": "invalid_request"}
        if (
            p.get("response_type") != "code"
            or p.get("code_challenge_method") != "S256"
            or not re.fullmatch(r"[A-Za-z0-9_-]{43}", p.get("code_challenge", ""))
            or not 16 <= len(p.get("state", "")) <= 128
        ):
            return 400, {"error": "invalid_request"}
        if p.get("scope") != SCOPE:
            return 400, {"error": "invalid_scope"}
        if p.get("decision") not in ("allow", "deny"):
            return 400, {"error": "invalid_request"}
        result = {"state": p["state"]}
        if p["decision"] == "deny":
            result["error"] = "access_denied"
        else:
            code = secrets.token_urlsafe(32)
            with self.lock, self.db:
                if self.db.execute("SELECT count(*) FROM codes").fetchone()[0] >= 512:
                    return 503, {"error": "fixture_capacity"}
                self.db.execute(
                    "INSERT INTO codes VALUES(?,?,?,0,NULL)",
                    (digest(code), p["code_challenge"], self.clock() + 15),
                )
            result["code"] = code
        return 302, {"location": CALLBACK + "?" + urllib.parse.urlencode(result)}

    def pair(self, family):
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.db.executemany(
            "INSERT INTO tokens VALUES(?,?,?,?,0)",
            [
                (digest(access), "access", family, self.clock() + self.ttl),
                (digest(refresh), "refresh", family, self.clock() + 60),
            ],
        )
        return {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": self.ttl,
            "refresh_token": refresh,
            "scope": SCOPE,
        }

    def exchange(self, p):
        if p.get("client_id") != CLIENT:
            return 400, {"error": "invalid_client"}
        with self.lock, self.db:
            if self.db.execute("SELECT count(*) FROM tokens").fetchone()[0] > 2046:
                return 503, {"error": "fixture_capacity"}
            if p.get("grant_type") == "authorization_code":
                if p.get("redirect_uri") != CALLBACK:
                    return 400, {"error": "invalid_grant"}
                try:
                    expected = challenge(p.get("code_verifier"))
                except ValueError:
                    return 400, {"error": "invalid_grant"}
                row = self.db.execute(
                    "SELECT challenge,expires,used,family FROM codes WHERE hash=?",
                    (digest(p.get("code", "")),),
                ).fetchone()
                if not row:
                    return 400, {"error": "invalid_grant"}
                if row[2]:
                    if row[3]:
                        self.db.execute("UPDATE families SET revoked=1 WHERE id=?", (row[3],))
                    return 400, {"error": "invalid_grant"}
                if row[1] <= self.clock() or (
                    self.mode != "weak-pkce" and not hmac.compare_digest(row[0], expected)
                ):
                    return 400, {"error": "invalid_grant"}
                family = secrets.token_urlsafe(24)
                self.db.execute("INSERT INTO families VALUES(?,0)", (family,))
                self.db.execute(
                    "UPDATE codes SET used=1,family=? WHERE hash=?", (family, digest(p["code"]))
                )
                return 200, self.pair(family)
            if p.get("grant_type") == "refresh_token":
                row = self.db.execute(
                    "SELECT t.family,t.expires,t.used,f.revoked FROM tokens t JOIN families f ON f.id=t.family WHERE t.hash=? AND t.kind='refresh'",
                    (digest(p.get("refresh_token", "")),),
                ).fetchone()
                if not row or row[3]:
                    return 400, {"error": "invalid_grant"}
                if row[2] and self.mode != "reusable-refresh":
                    self.db.execute("UPDATE families SET revoked=1 WHERE id=?", (row[0],))
                    return 400, {"error": "invalid_grant"}
                if row[1] <= self.clock():
                    return 400, {"error": "invalid_grant"}
                self.db.execute(
                    "UPDATE tokens SET used=1 WHERE hash=?", (digest(p["refresh_token"]),)
                )
                return 200, self.pair(row[0])
            return 400, {"error": "unsupported_grant_type"}

    def resource(self, token):
        with self.lock:
            row = self.db.execute(
                "SELECT t.expires,f.revoked FROM tokens t JOIN families f ON f.id=t.family WHERE t.hash=? AND t.kind='access'",
                (digest(token),),
            ).fetchone()
            if not row or row[1] or row[0] <= self.clock():
                return 401, {"error": "invalid_token"}
        return 200, {
            "owner": "synthetic-training-user",
            "scope": SCOPE,
            "backend": "offline-fixture",
        }

    def revoke(self, p):
        if p.get("client_id") != CLIENT:
            return 400, {"error": "invalid_client"}
        with self.lock, self.db:
            row = self.db.execute(
                "SELECT family FROM tokens WHERE hash=?", (digest(p.get("token", "")),)
            ).fetchone()
            if row:
                self.db.execute("UPDATE families SET revoked=1 WHERE id=?", (row[0],))
        return 200, {}


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store):
        isolated_address(address[0])
        self.store = store
        super().__init__(address, Handler)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, data):
        payload = b"" if status == 302 else json.dumps(data, sort_keys=True).encode()
        self.send_response(status)
        if status == 302:
            self.send_header("Location", data["location"])
        else:
            self.send_header("Content-Type", "application/json")
        if status == 401:
            self.send_header(
                "WWW-Authenticate", 'Bearer realm="isolated-oauth", error="invalid_token"'
            )
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        try:
            url = urllib.parse.urlsplit(self.path)
            if url.path == "/authorize":
                return self.reply(*self.server.store.issue_code(parameters(url.query)))
            if url.path == "/resource":
                auth = self.headers.get("Authorization", "")
                return self.reply(
                    *self.server.store.resource(auth[7:] if auth.startswith("Bearer ") else "")
                )
            if url.path == "/health":
                return self.reply(200, {"fixture": "oauth-subset", "synthetic_user": True})
            self.reply(404, {"error": "not_found"})
        except (ValueError, UnicodeError):
            self.reply(400, {"error": "invalid_request"})

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if (
                not 0 < size <= 4096
                or self.headers.get("Content-Type", "").split(";")[0]
                != "application/x-www-form-urlencoded"
            ):
                raise ValueError("invalid body")
            p = parameters(self.rfile.read(size).decode("utf-8"))
            if self.path == "/control":
                if self.headers.get("X-Lab-Control") != "public-training-fixture":
                    return self.reply(403, {"error": "fixture_control_denied"})
                if set(p) != {"mode"} or p["mode"] not in (
                    "healthy",
                    "weak-pkce",
                    "reusable-refresh",
                ):
                    return self.reply(400, {"error": "invalid_fixture_mode"})
                with self.server.store.lock:
                    self.server.store.mode = p["mode"]
                return self.reply(200, {"configured": True, "mode": p["mode"]})
            if self.path == "/token":
                return self.reply(*self.server.store.exchange(p))
            if self.path == "/revoke":
                return self.reply(*self.server.store.revoke(p))
            self.reply(404, {"error": "not_found"})
        except (ValueError, UnicodeError):
            self.reply(400, {"error": "invalid_request"})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class Client:
    def __init__(self, base):
        u = urllib.parse.urlsplit(base)
        ip = ipaddress.ip_address(u.hostname)
        if (
            u.scheme != "http"
            or u.username
            or u.password
            or u.path not in ("", "/")
            or u.query
            or u.fragment
            or ip.version != 4
            or not (ip.is_loopback or ip in ipaddress.ip_network("198.18.0.0/15"))
        ):
            raise ValueError("not an isolated fixture address")
        self.base = base.rstrip("/")
        self.open = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, path, p=None, token=None, control=False):
        body = None if p is None else urllib.parse.urlencode(p).encode()
        headers = {} if body is None else {"Content-Type": "application/x-www-form-urlencoded"}
        if control:
            headers["X-Lab-Control"] = "public-training-fixture"
        if token:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(self.base + path, data=body, headers=headers)
        try:
            r = self.open.open(request, timeout=3)
        except urllib.error.HTTPError as e:
            r = e
        with r:
            raw = r.read(8193)
            if len(raw) > 8192:
                raise ValueError("oversized fixture response")
            return r.status, dict(r.headers), json.loads(raw) if raw else {}

    def authorization(self, decision="allow"):
        verifier = secrets.token_urlsafe(32)
        state = secrets.token_urlsafe(24)
        p = {
            "client_id": CLIENT,
            "redirect_uri": CALLBACK,
            "response_type": "code",
            "code_challenge_method": "S256",
            "code_challenge": challenge(verifier),
            "state": state,
            "scope": SCOPE,
            "decision": decision,
        }
        status, headers, _ = self.request("/authorize?" + urllib.parse.urlencode(p))
        assert status == 302
        return headers["Location"], state, verifier

    @staticmethod
    def callback(location, state):
        u = urllib.parse.urlsplit(location)
        if urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, "", "")) != CALLBACK or u.fragment:
            raise ValueError("wrong callback")
        p = parameters(u.query)
        if not hmac.compare_digest(p.get("state", "").encode("utf-8"), state.encode("utf-8")):
            raise ValueError("state mismatch")
        if p.get("error"):
            raise ValueError(p["error"])
        if not p.get("code"):
            raise ValueError("missing code")
        return p["code"]

    def redeem(self, code, verifier, redirect=CALLBACK):
        return self.request(
            "/token",
            {
                "grant_type": "authorization_code",
                "client_id": CLIENT,
                "redirect_uri": redirect,
                "code": code,
                "code_verifier": verifier,
            },
        )

    def login(self):
        location, state, verifier = self.authorization()
        status, _, pair = self.redeem(self.callback(location, state), verifier)
        assert status == 200
        return pair


def probe(base, mode, phase="baseline"):
    c = Client(base)
    checks = []
    if phase == "fault":
        if mode == "code":
            location, state, verifier = c.authorization()
            code = c.callback(location, state)
            status, _, issued = c.redeem(code, "A" * 43)
            assert status == 200 and c.request("/resource", token=issued["access_token"])[0] == 200
            checks = [
                "controlled weak-PKCE fault actually admits the wrong verifier and exposes the resource"
            ]
        elif mode == "refresh":
            pair = c.login()
            p = {
                "grant_type": "refresh_token",
                "client_id": CLIENT,
                "refresh_token": pair["refresh_token"],
            }
            assert c.request("/token", p)[0] == 200
            status, _, replayed = c.request("/token", p)
            assert (
                status == 200 and c.request("/resource", token=replayed["access_token"])[0] == 200
            )
            checks = [
                "controlled rotation fault actually allows replay of the consumed refresh credential"
            ]
        else:
            raise ValueError("unknown probe")
        return {
            "status": "passed",
            "mode": mode,
            "phase": phase,
            "vulnerability_observed": True,
            "checks": checks,
            "backend": "offline-fixture",
            "tokens_logged": False,
        }
    if mode == "code":
        location, state, verifier = c.authorization()
        try:
            c.callback(location, "different-state")
        except ValueError as e:
            assert str(e) == "state mismatch"
        else:
            raise AssertionError("CSRF state accepted")
        code = c.callback(location, state)
        assert c.redeem(code, "A" * 43)[0] == 400
        assert c.redeem(code, verifier, CALLBACK + "-wrong")[0] == 400
        status, _, pair = c.redeem(code, verifier)
        assert status == 200
        assert c.request("/resource", token=pair["access_token"])[0] == 200
        assert c.redeem(code, verifier)[0] == 400
        assert c.request("/resource", token=pair["access_token"])[0] == 401
        denied, s, _ = c.authorization("deny")
        try:
            c.callback(denied, s)
        except ValueError as e:
            assert str(e) == "access_denied"
        else:
            raise AssertionError("denied consent issued a code")
        checks = [
            "state mismatch rejected before exchange",
            "exact redirect and S256 verifier enforced",
            "single-use code replay revokes issued family",
            "explicit synthetic consent denial produces no usable grant",
        ]
    elif mode == "refresh":
        pair = c.login()
        assert c.request("/resource", token=pair["access_token"])[0] == 200
        time.sleep(pair["expires_in"] + 0.2)
        assert c.request("/resource", token=pair["access_token"])[0] == 401

        def refresh(t):
            return c.request(
                "/token", {"grant_type": "refresh_token", "client_id": CLIENT, "refresh_token": t}
            )

        status, _, new = refresh(pair["refresh_token"])
        assert status == 200 and new["refresh_token"] != pair["refresh_token"]
        assert c.request("/resource", token=new["access_token"])[0] == 200
        assert refresh(pair["refresh_token"])[0] == 400
        assert (
            c.request("/resource", token=new["access_token"])[0] == 401
            and refresh(new["refresh_token"])[0] == 400
        )
        pair = c.login()
        assert c.request("/resource", token=pair["access_token"])[0] == 200
        assert c.request("/revoke", {"client_id": CLIENT, "token": pair["refresh_token"]})[0] == 200
        assert c.request("/resource", token=pair["access_token"])[0] == 401
        checks = [
            "real access-token expiry",
            "refresh rotation issues a new credential",
            "old refresh replay revokes the entire family",
            "fresh authorization recovers; explicit revocation closes access",
        ]
    else:
        raise ValueError("unknown probe")
    return {
        "status": "passed",
        "mode": mode,
        "phase": phase,
        "checks": checks,
        "backend": "offline-fixture",
        "tokens_logged": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["serve", "code", "refresh", "configure"])
    parser.add_argument("--bind", default="198.18.0.1")
    parser.add_argument("--base", default="http://198.18.0.1:8080")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db", type=Path, default=Path("/lab/oauth.sqlite"))
    parser.add_argument("--phase", choices=["baseline", "fault", "recovered"], default="baseline")
    parser.add_argument(
        "--mode", choices=["healthy", "weak-pkce", "reusable-refresh"], default="healthy"
    )
    a = parser.parse_args()
    if a.action == "serve":
        Server((a.bind, a.port), Store(a.db)).serve_forever()
    elif a.action == "configure":
        status, _, result = Client(a.base).request("/control", {"mode": a.mode}, control=True)
        assert status == 200 and result["configured"] is True
        print(json.dumps(result, sort_keys=True))
    else:
        print(json.dumps(probe(a.base, a.action, a.phase), sort_keys=True))
