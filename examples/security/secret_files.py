"""Real POSIX ownership, scoped injection and live credential rotation in one isolated guest."""

import argparse
import hmac
import http.server
import json
import os
import re
import secrets
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-SECRET-FILES-V1"
SERVICE, UNTRUSTED = 1500, 1501
URL = "http://127.0.0.1:18081/protected"


def folder():
    p = ROOT / "secret-demo"
    info = p.lstat()
    assert stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o755
    return p


def keypath():
    p = folder() / "runtime.key"
    info = p.lstat()
    assert (
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and info.st_uid == 0
        and info.st_gid == SERVICE
    )
    assert stat.S_IMODE(info.st_mode) in (0o440, 0o444)
    return p


def valid_key(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{32}", value) is not None


def allowed(header, key):
    return (
        valid_key(key)
        and isinstance(header, str)
        and header.isascii()
        and hmac.compare_digest(header, "Bearer " + key)
    )


def install():
    base = ROOT / "secret-demo"
    base.mkdir(mode=0o755)
    os.chmod(base, 0o755)
    p = folder() / "runtime.key"
    with p.open("x") as stream:
        stream.write(secrets.token_hex(16))
    os.chown(p, 0, SERVICE)
    os.chmod(p, 0o440)
    with (base / "server.log").open("ab") as output:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "serve"],
            user=SERVICE,
            group=SERVICE,
            extra_groups=[],
            cwd=str(base),
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(base)},
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    (base / "server.pid").write_text(str(child.pid))
    os.chmod(base / "server.pid", 0o644)
    return {"status": "passed", "configured": True}


def request(key=None):
    headers = {} if key is None else {"Authorization": "Bearer " + key}
    try:
        with urllib.request.urlopen(
            urllib.request.Request(URL, headers=headers), timeout=3
        ) as response:
            data = json.load(response)
            assert set(data) == {"service_uid", "service_pid", "secret_in_process_metadata"}
            assert data["service_pid"] == int((folder() / "server.pid").read_text())
            assert data["service_uid"] == SERVICE and data["secret_in_process_metadata"] is False
            return response.status
    except urllib.error.HTTPError as error:
        assert error.code == 401
        return error.code


def process_exposure(key, argv, environment):
    assert valid_key(key) and isinstance(argv, bytes) and isinstance(environment, bytes)
    return key.encode() in argv or key.encode() in environment


def serve():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/protected":
                self.send_error(404)
                return
            key = keypath().read_text()
            if not allowed(self.headers.get("Authorization"), key):
                self.send_response(401)
                self.end_headers()
                return
            exposed = process_exposure(
                key,
                Path("/proc/self/cmdline").read_bytes(),
                Path("/proc/self/environ").read_bytes(),
            )
            body = json.dumps(
                {
                    "service_uid": os.geteuid(),
                    "service_pid": os.getpid(),
                    "secret_in_process_metadata": exposed,
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    http.server.HTTPServer(("127.0.0.1", 18081), Handler).serve_forever()


def child(action):
    assert os.geteuid() in (SERVICE, UNTRUSTED)
    denied = False
    if action == "read":
        try:
            key = keypath().read_text()
        except PermissionError:
            key, denied = None, True
    else:
        key = sys.stdin.read(128)
        assert valid_key(key)
        try:
            keypath().read_text()
        except PermissionError:
            denied = True
    write_denied = False
    try:
        descriptor = os.open(keypath(), os.O_WRONLY)
    except PermissionError:
        write_denied = True
    else:
        os.close(descriptor)
    return {
        "uid": os.geteuid(),
        "read_denied": denied,
        "write_denied": write_denied,
        "api_status": request(key),
    }


def as_user(uid, action="read", prior=None):
    assert uid in (SERVICE, UNTRUSTED) and action in ("read", "replay")
    command = [sys.executable, str(Path(__file__).resolve()), "child", "--child-action", action]
    result = subprocess.run(
        command,
        user=uid,
        group=uid,
        extra_groups=[],
        cwd=str(folder()),
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(folder())},
        input=prior if prior is not None else "",
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    value = json.loads(result.stdout)
    assert (
        set(value) == {"uid", "read_denied", "write_denied", "api_status"} and value["uid"] == uid
    )
    return value


def expect_user(uid, denied, status, action="read", prior=None):
    value = as_user(uid, action, prior)
    assert (
        value["read_denied"] is denied
        and value["write_denied"] is True
        and value["api_status"] == status
    )


def baseline():
    p = keypath()
    assert stat.S_IMODE(p.stat().st_mode) == 0o440
    expect_user(SERVICE, False, 200)
    expect_user(UNTRUSTED, True, 401)
    return {
        "status": "passed",
        "service_uid": SERVICE,
        "untrusted_uid": UNTRUSTED,
        "untrusted_file_denied": True,
        "untrusted_api_status": 401,
        "service_api_status": 200,
        "secrets_logged": False,
    }


def expose():
    p = keypath()
    assert stat.S_IMODE(p.stat().st_mode) == 0o440
    compromised = folder() / "compromised.key"
    descriptor = os.open(compromised, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(p.read_text())
    os.chmod(p, 0o444)
    expect_user(UNTRUSTED, False, 200)
    expect_user(SERVICE, False, 200)
    return {
        "status": "passed",
        "vulnerability_observed": True,
        "untrusted_file_denied": False,
        "untrusted_api_status": 200,
        "secrets_logged": False,
    }


def exposed():
    assert stat.S_IMODE(keypath().stat().st_mode) == 0o444
    expect_user(UNTRUSTED, False, 200)
    expect_user(SERVICE, False, 200)
    return {
        "status": "passed",
        "vulnerability_observed": True,
        "untrusted_api_status": 200,
        "secrets_logged": False,
    }


def recovered():
    baseline()
    old = (folder() / "compromised.key").read_text()
    assert valid_key(old)
    expect_user(UNTRUSTED, True, 401, "replay", old)
    return {
        "status": "passed",
        "old_credential_api_status": 401,
        "untrusted_file_denied": True,
        "service_api_status": 200,
        "rotation_invalidated_cached_key": True,
        "secrets_logged": False,
    }


def repair():
    p = keypath()
    assert stat.S_IMODE(p.stat().st_mode) == 0o444
    captured = folder() / "compromised.key"
    info = captured.lstat()
    assert (
        stat.S_ISREG(info.st_mode)
        and info.st_nlink == 1
        and info.st_uid == 0
        and stat.S_IMODE(info.st_mode) == 0o600
    )
    old = captured.read_text()
    assert valid_key(old)
    os.chmod(p, 0o440)
    replacement = folder() / "runtime.next"
    descriptor = os.open(replacement, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(secrets.token_hex(16))
    os.chown(replacement, 0, SERVICE)
    os.chmod(replacement, 0o440)
    replacement.replace(p)
    assert not hmac.compare_digest(old, p.read_text())
    expect_user(UNTRUSTED, True, 401, "replay", old)
    baseline()
    return {
        "status": "passed",
        "old_credential_api_status": 401,
        "untrusted_file_denied": True,
        "service_api_status": 200,
        "rotation_invalidated_cached_key": True,
        "secrets_logged": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "configure",
            "serve",
            "child",
            "baseline",
            "expose",
            "repair",
            "exposed",
            "recovered",
        ],
    )
    parser.add_argument("--child-action", choices=["read", "replay"], default="read")
    args = parser.parse_args()
    assert (ROOT / "CML-SECRETS-FIXTURE").read_text().strip() == MARKER
    if args.action == "serve":
        assert os.geteuid() == SERVICE
        serve()
        return
    if args.action == "child":
        value = child(args.child_action)
    else:
        assert os.geteuid() == 0
        if args.action == "configure":
            value = install()
        elif args.action == "baseline":
            value = baseline()
        elif args.action == "expose":
            value = expose()
        elif args.action == "exposed":
            value = exposed()
        elif args.action == "recovered":
            value = recovered()
        else:
            value = repair()
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
