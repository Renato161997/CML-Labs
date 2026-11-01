"""Isolated UDP/TOS observations for a real routed MQC exercise."""

import argparse
import http.server
import ipaddress
import json
import os
import re
import secrets
import select
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-QOS-DATAPLANE-V1"
CLIENT, SERVER = "198.18.0.2", "198.18.1.2"
LIMITS = {"data": 16, "control": 4}
PORTS = {"data": 9000, "control": 9001}
SIZES = {"data": 1000, "control": 100}


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=15)


def configure(role):
    own, gateway = (CLIENT, "198.18.0.1") if role == "CLIENT" else (SERVER, "198.18.1.1")
    remote = SERVER if role == "CLIENT" else CLIENT
    run(["ip", "link", "set", "eth1", "up"])
    run(["ip", "addr", "add", own + "/30", "dev", "eth1"])
    prefix = str(ipaddress.IPv4Network(remote + "/30", strict=False))
    run(["ip", "route", "add", prefix, "via", gateway, "dev", "eth1"])
    if role == "SERVER":
        with (ROOT / "qos-server.log").open("ab") as output:
            child = subprocess.Popen(
                ["python3", str(Path(__file__).resolve()), "serve"],
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        (ROOT / "qos-server.pid").write_text(str(child.pid))
    return {"status": "passed", "role": role}


def packet(nonce, kind, sequence):
    assert re.fullmatch("[0-9a-f]{24}", nonce) and kind in LIMITS
    assert type(sequence) is int and 0 <= sequence < LIMITS[kind]
    value = json.dumps(
        {"nonce": nonce, "kind": kind, "sequence": sequence}, separators=(",", ":")
    ).encode("ascii")
    return value.ljust(SIZES[kind], b" ")


def decode(raw, kind):
    if kind not in LIMITS or len(raw) != SIZES[kind]:
        raise ValueError("Unexpected kind or UDP payload size")
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {"nonce", "kind", "sequence"}:
        raise ValueError("Unexpected payload fields")
    if not isinstance(value["nonce"], str) or not re.fullmatch("[0-9a-f]{24}", value["nonce"]):
        raise ValueError("Invalid evidence generation")
    if (
        value["kind"] != kind
        or type(value["sequence"]) is not int
        or not 0 <= value["sequence"] < LIMITS[kind]
    ):
        raise ValueError("Invalid traffic class or sequence")
    return value


class Observations:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset("0" * 24)

    def reset(self, nonce):
        if not re.fullmatch("[0-9a-f]{24}", nonce):
            raise ValueError("Invalid generation")
        with self.lock:
            self.nonce = nonce
            self.sequences = {name: set() for name in LIMITS}
            self.tos = {name: set() for name in LIMITS}
            self.malformed = self.duplicates = 0

    def receive(self, raw, kind, tos):
        with self.lock:
            try:
                value = decode(raw, kind)
                if type(tos) is not int or not 0 <= tos <= 255:
                    raise ValueError("Missing or invalid received TOS")
            except (ValueError, TypeError, UnicodeError):
                self.malformed += 1
                return
            if value["nonce"] != self.nonce:
                return
            sequence = value["sequence"]
            if sequence in self.sequences[kind]:
                self.duplicates += 1
            self.sequences[kind].add(sequence)
            self.tos[kind].add(tos)

    def snapshot(self, nonce):
        with self.lock:
            if nonce != self.nonce:
                raise ValueError("Stale generation")
            return {
                "sequences": {k: sorted(v) for k, v in self.sequences.items()},
                "tos": {k: sorted(v) for k, v in self.tos.items()},
                "malformed": self.malformed,
                "duplicates": self.duplicates,
            }


def serve():
    state = Observations()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if (
                self.client_address[0] != CLIENT
                or self.path != "/window"
                or self.headers.get("Content-Length") != "24"
            ):
                self.send_error(400)
                return
            try:
                state.reset(self.rfile.read(24).decode("ascii"))
            except (ValueError, UnicodeError):
                self.send_error(400)
                return
            self.send_response(204)
            self.end_headers()

        def do_GET(self):
            if self.client_address[0] != CLIENT or not re.fullmatch(
                "/window/[0-9a-f]{24}", self.path
            ):
                self.send_error(400)
                return
            try:
                body = json.dumps(state.snapshot(self.path.rsplit("/", 1)[1])).encode()
            except ValueError:
                self.send_error(409)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = http.server.ThreadingHTTPServer((SERVER, 8081), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    receivers = {}
    for kind, port in PORTS.items():
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.setsockopt(socket.IPPROTO_IP, socket.IP_RECVTOS, 1)
        receiver.bind((SERVER, port))
        receivers[receiver] = kind
    try:
        while True:
            for receiver in select.select(list(receivers), [], [], 0.2)[0]:
                raw, ancillary, flags, peer = receiver.recvmsg(4096, 64)
                if peer[0] != CLIENT:
                    continue
                observed = [
                    data[0]
                    for level, option, data in ancillary
                    if level == socket.IPPROTO_IP and option == socket.IP_TOS and len(data) == 1
                ]
                state.receive(
                    raw,
                    receivers[receiver],
                    observed[0] if len(observed) == 1 and flags == 0 else None,
                )
    finally:
        httpd.shutdown()
        httpd.server_close()
        for receiver in receivers:
            receiver.close()


def accepted(value, mode):
    if mode not in ("marked", "unmarked", "limited"):
        return False
    if value["malformed"] != 0 or value["duplicates"] != 0:
        return False
    if value["sequences"]["control"] != list(range(LIMITS["control"])) or value["tos"][
        "control"
    ] != [0]:
        return False
    actual = value["sequences"]["data"]
    if mode == "limited":
        enough = (
            0 < len(actual) < LIMITS["data"]
            and len(set(actual)) == len(actual)
            and all(type(v) is int and 0 <= v < LIMITS["data"] for v in actual)
        )
    else:
        enough = actual == list(range(LIMITS["data"]))
    return enough and value["tos"]["data"] == ([0] if mode == "unmarked" else [184])


def probe(mode):
    assert mode in ("marked", "unmarked", "limited")
    nonce = secrets.token_hex(12)
    base = "http://" + SERVER + ":8081/window"
    with urllib.request.urlopen(
        urllib.request.Request(base, data=nonce.encode(), method="POST"), timeout=5
    ) as response:
        assert response.status == 204
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.bind((CLIENT, 0))
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0)
        for kind, count in LIMITS.items():
            for sequence in range(count):
                sender.sendto(packet(nonce, kind, sequence), (SERVER, PORTS[kind]))
                time.sleep(0.01)
    deadline = time.monotonic() + 3
    settled_since, prior = None, None
    while True:
        with urllib.request.urlopen(base + "/" + nonce, timeout=5) as response:
            value = json.load(response)
        if value == prior:
            if (
                settled_since is not None
                and time.monotonic() - settled_since >= 0.5
                and value["sequences"]["control"] == list(range(4))
            ):
                break
        else:
            prior, settled_since = value, time.monotonic()
        if time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    assert accepted(value, mode), value
    return {
        "status": "passed",
        "mode": mode,
        "data_received": len(value["sequences"]["data"]),
        "control_received": 4,
        "observed_data_tos": value["tos"]["data"],
        "observed_control_tos": value["tos"]["control"],
        "fresh_generation": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["configure", "serve", "marked", "unmarked", "limited"])
    action = parser.parse_args().action
    if os.geteuid() != 0 or (ROOT / "CML-QOS-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the isolated marked QoS fixture is accepted")
    role = (ROOT / "qos-role").read_text().strip()
    assert role in ("CLIENT", "SERVER")
    if action == "configure":
        value = configure(role)
    elif action == "serve":
        assert role == "SERVER"
        serve()
        return
    else:
        assert role == "CLIENT"
        value = probe(action)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
