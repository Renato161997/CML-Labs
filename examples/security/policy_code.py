"""Closed classroom ACL compiler and staged HTTP artifact publisher."""

import argparse
import copy
import hashlib
import http.server
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-POLICY-CODE-V1"


def intent(version=1, application="allow"):
    return {
        "version": version,
        "source": "198.18.10.10/32",
        "target": "198.18.20.20/32",
        "application": application,
        "administration": "deny",
        "icmp": "allow",
    }


def compile_policy(value):
    if not isinstance(value, dict) or set(value) != {
        "version",
        "source",
        "target",
        "application",
        "administration",
        "icmp",
    }:
        raise ValueError("Only the closed exercise intent fields are accepted")
    if type(value["version"]) is not int or not 1 <= value["version"] <= 100:
        raise ValueError("Invalid bounded version")
    if value["source"] != "198.18.10.10/32" or value["target"] != "198.18.20.20/32":
        raise ValueError("Intent changes the approved exercise resource scope")
    if (
        value["application"] not in ("allow", "deny")
        or value["administration"] != "deny"
        or value["icmp"] != "allow"
    ):
        raise ValueError("Intent violates the administration/control invariants")
    action = "permit" if value["application"] == "allow" else "deny"
    return (
        "! CML classroom ACL intent version " + str(value["version"]) + "\n"
        "ip access-list extended POLICY-CODE\n"
        " no 10\n"
        " 10 " + action + " tcp host 198.18.10.10 host 198.18.20.20 eq 8080\n"
        " no 20\n"
        " 20 deny tcp any host 198.18.20.20 eq 9090\n"
        " no 30\n"
        " 30 permit icmp any any\n"
        " no 40\n"
        " 40 deny ip any any\n"
        " exit\n"
        "end\n"
    )


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def state_read(path):
    if path.is_symlink():
        raise ValueError("Artifact links are refused")
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or set(value) != {"intent", "body", "sha256"}:
        raise ValueError("Invalid artifact envelope")
    expected = compile_policy(value["intent"])
    if value["body"] != expected or value["sha256"] != digest(expected):
        raise ValueError("Artifact does not match accepted intent")
    return value


def publish(value, path):
    body = compile_policy(value)
    result = {"intent": copy.deepcopy(value), "body": body, "sha256": digest(body)}
    if path.is_symlink():
        raise ValueError("Artifact links are refused")
    temp = path.with_suffix(".next")
    with temp.open("x") as output:
        json.dump(result, output, sort_keys=True)
    temp.chmod(0o600)
    temp.replace(path)
    return result


def refuse_unsafe(path):
    before = path.read_bytes()
    current = state_read(path)
    samples = [
        dict(current["intent"], administration="allow"),
        dict(current["intent"], source="0.0.0.0/0"),
        dict(current["intent"], target="0.0.0.0/0"),
        dict(current["intent"], version=True),
        dict(current["intent"], commands=["permit ip any any"]),
    ]
    for value in samples:
        try:
            publish(value, path)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsafe intent was published")
        assert path.read_bytes() == before
    return {
        "status": "passed",
        "unsafe_candidates_rejected": len(samples),
        "artifact_unchanged": True,
        "sha256": current["sha256"],
    }


def make_server(address):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/approved":
                self.send_error(404)
                return
            try:
                value = state_read(ROOT / "approved.json")
                raw = value["body"].encode("utf-8")
            except (OSError, ValueError, TypeError, KeyError):
                self.send_error(503)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("ETag", '"' + value["sha256"] + '"')
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    return http.server.HTTPServer(address, Handler)


def configure():
    value = publish(intent(), ROOT / "approved.json")
    publish(intent(), ROOT / "rollback.json")
    with (ROOT / "policy-http.log").open("ab") as output:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "serve"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return {"status": "passed", "version": value["intent"]["version"], "sha256": value["sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("configure", "serve", "reject-unsafe", "block", "rollback", "state")
    )
    action = parser.parse_args().action
    if os.geteuid() != 0 or (ROOT / "CML-POLICY-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the marked exercise publisher is accepted")
    if action == "configure":
        value = configure()
    elif action == "serve":
        make_server(("198.18.10.10", 8081)).serve_forever()
        return
    elif action == "reject-unsafe":
        value = refuse_unsafe(ROOT / "approved.json")
    elif action == "block":
        result = publish(intent(2, "deny"), ROOT / "approved.json")
        value = {
            "status": "passed",
            "application": "deny",
            "version": 2,
            "sha256": result["sha256"],
        }
    elif action == "rollback":
        previous = state_read(ROOT / "rollback.json")
        result = publish(previous["intent"], ROOT / "approved.json")
        value = {
            "status": "passed",
            "application": "allow",
            "version": result["intent"]["version"],
            "sha256": result["sha256"],
        }
    else:
        result = state_read(ROOT / "approved.json")
        value = {
            "status": "passed",
            "application": result["intent"]["application"],
            "version": result["intent"]["version"],
            "sha256": result["sha256"],
        }
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
