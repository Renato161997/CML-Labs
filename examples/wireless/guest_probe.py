"""Real WPA2 guest traffic and a narrowly scoped IPv4 forwarding policy."""

import argparse
import errno
import http.client
import ipaddress
import json
import os
import re
import subprocess
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import radio_probe as radio

ROOT = Path("/lab")
PROC = Path("/proc")
GUEST = "198.18.10.2"
GATEWAY = "198.18.10.1"
INSIDE = "198.18.20.2"
UPLINK = "198.18.20.1"
SHARED = "192.0.2.80"
PROTECTED = "198.18.20.0/30"
PRIORITY = 12345


def role():
    value = json.loads((ROOT / "guest-role.json").read_text())
    if (
        not isinstance(value, dict)
        or set(value) != {"role"}
        or value["role"] not in ("ap", "client", "inside")
    ):
        raise ValueError("Unexpected guest exercise role")
    return value["role"]


def rule_is_exact(rule):
    forbidden = {
        "not",
        "iif_detached",
        "oif",
        "fwmark",
        "fwmask",
        "tos",
        "uid_start",
        "uid_end",
        "ipproto",
        "sport",
        "dport",
        "l3mdev",
        "tun_id",
        "dscp",
        "flowlabel",
    }
    assert not forbidden.intersection(rule), rule
    assert (
        rule.get("priority") == PRIORITY and rule.get("src") == "all" and rule.get("srclen", 0) == 0
    ), rule
    assert rule.get("iif") == "wlan0" and rule.get("action") == "prohibit", rule
    assert (
        str(ipaddress.IPv4Network((rule["dst"], rule.get("dstlen", 32)), strict=True)) == PROTECTED
    ), rule


def policy_state():
    rules = json.loads(radio.run_command(["ip", "-j", "rule", "show"]).stdout)
    selected = [value for value in rules if value.get("priority") == PRIORITY]
    assert len(selected) <= 1, "The fixture priority must not collide with other policy rules"
    if selected:
        rule_is_exact(selected[0])
    return bool(selected)


def policy(enabled):
    if type(enabled) is not bool:
        raise ValueError("An explicit policy boolean is required")
    present = policy_state()
    if present != enabled:
        radio.run_command(
            [
                "ip",
                "rule",
                "add" if enabled else "del",
                "priority",
                str(PRIORITY),
                "iif",
                "wlan0",
                "to",
                PROTECTED,
                "prohibit",
            ]
        )
        radio.run_command(["ip", "-4", "route", "flush", "cache"])
    assert policy_state() == enabled
    return {"policy_enabled": enabled}


def make_server(address, kind):
    if kind not in ("ap", "inside"):
        raise ValueError("A WLAN client cannot provide an experiment endpoint")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            match = re.fullmatch(r"/probe\?nonce=([0-9a-f]{32})", self.path)
            if not match:
                self.send_error(400)
                return
            raw = json.dumps(
                {"marker": radio.MARKER, "role": kind, "nonce": match[1], "pid": os.getpid()},
                sort_keys=True,
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

    return ThreadingHTTPServer(address, Handler)


def response(value, nonce, expected_role):
    assert isinstance(value, dict) and set(value) == {"marker", "role", "nonce", "pid"}
    assert (
        value["marker"] == radio.MARKER
        and value["role"] == expected_role
        and value["nonce"] == nonce
    )
    assert type(value["pid"]) is int and value["pid"] > 1
    return value


def request(target, source):
    if target not in (SHARED, INSIDE) or source not in (GUEST, UPLINK, INSIDE):
        raise ValueError("Only the declared benchmark endpoints and source addresses are accepted")
    nonce = uuid.uuid4().hex
    connection = http.client.HTTPConnection(target, 8080, timeout=4, source_address=(source, 0))
    try:
        connection.request("GET", "/probe?nonce=" + nonce)
        result = connection.getresponse()
        raw = result.read(2049)
        assert (
            result.status == 200
            and result.getheader("Content-Type") == "application/json"
            and len(raw) <= 2048
        )
        return response(json.loads(raw), nonce, "ap" if target == SHARED else "inside")
    finally:
        connection.close()


def http_owned(pid):
    if type(pid) is not int or pid <= 1:
        raise ValueError("Unsafe endpoint PID")
    try:
        args = (PROC / str(pid) / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    except FileNotFoundError:
        return False
    return args == [os.fsencode(sys.executable), os.fsencode(Path(__file__).resolve()), b"serve"]


def start(kind):
    target, source = (SHARED, UPLINK) if kind == "ap" else (INSIDE, INSIDE)
    path = ROOT / "guest-http.pid"
    if path.exists() and http_owned(int(path.read_text())):
        assert request(target, source)["pid"] == int(path.read_text())
        return
    with (ROOT / "guest-http.log").open("ab") as output:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "serve"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            start_new_session=True,
        )
    path.write_text(str(child.pid))
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        assert child.poll() is None, "The owned endpoint exited during startup"
        try:
            assert http_owned(child.pid) and request(target, source)["pid"] == child.pid
            return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError("The owned HTTP endpoint did not start")


def configure(kind):
    if kind == "inside":
        radio.run_command(
            ["ip", "route", "replace", "198.18.10.0/24", "via", UPLINK, "dev", "eth1"]
        )
        start(kind)
        return {"configured": True, "role": kind}
    value = radio.settings(json.loads((ROOT / "wireless.json").read_text()))
    assert value["role"] == kind and value["auth"] == "wpa2"
    radio.configure(value, "none")
    radio.run_command(
        [
            "ip",
            "address",
            "del",
            (radio.TARGET if kind == "ap" else radio.CLIENT) + "/24",
            "dev",
            "wlan0",
        ]
    )
    radio.run_command(
        ["ip", "address", "replace", (GATEWAY if kind == "ap" else GUEST) + "/24", "dev", "wlan0"]
    )
    if kind == "client":
        for prefix in (PROTECTED, SHARED + "/32"):
            radio.run_command(["ip", "route", "replace", prefix, "via", GATEWAY, "dev", "wlan0"])
    else:
        radio.run_command(["ip", "address", "replace", UPLINK + "/30", "dev", "ens2"])
        radio.run_command(["ip", "link", "set", "dev", "ens2", "up"])
        radio.run_command(["ip", "address", "replace", SHARED + "/32", "dev", "lo"])
        radio.run_command(["sysctl", "-w", "net.ipv4.ip_forward=1"])
        policy(True)
        start(kind)
    return {"configured": True, "role": kind}


def ping(target, device, received):
    result = radio.run_command(["ping", "-I", device, "-c", "3", "-W", "2", target], check=False)
    assert radio.packet_counts(result.stdout) == (3, received)
    assert (result.returncode == 0) == (received == 3)


def associated():
    value = radio.settings(json.loads((ROOT / "wireless.json").read_text()))
    status, link = radio.snapshot()
    assert value["role"] == "client" and value["auth"] == "wpa2"
    assert all(radio.association(status, link, value).values())


def explicit_denial(error):
    assert type(error.errno) is int and error.errno in (
        errno.EHOSTUNREACH,
        errno.ENETUNREACH,
        errno.EACCES,
        errno.EPERM,
    ), "Only explicit network-policy rejection is accepted; refusal and timeout are not proof"


def check(kind, expected, enabled):
    if kind == "inside":
        request(INSIDE, INSIDE)
        return {"status": "passed", "role": kind, "endpoint_healthy": True}
    if kind == "ap":
        value = radio.settings(json.loads((ROOT / "wireless.json").read_text()))
        status = radio.parse_status(
            radio.run_command(["hostapd_cli", "-i", "wlan0", "status"]).stdout
        )
        assert status.get("state") == "ENABLED" and status.get("ssid[0]") == value["ssid"]
        assert policy_state() == enabled
        ping(INSIDE, "ens2", 3)
        request(INSIDE, UPLINK)
        request(SHARED, UPLINK)
        return {
            "status": "passed",
            "role": kind,
            "policy_enabled": enabled,
            "inside_control_received": 3,
        }
    deadline = time.monotonic() + 45
    while True:
        try:
            associated()
            break
        except AssertionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)
    rows = json.loads(radio.run_command(["ip", "-j", "address", "show", "dev", "wlan0"]).stdout)
    assert len(rows) == 1 and "UP" in rows[0]["flags"]
    assert {
        (item["local"], item["prefixlen"])
        for item in rows[0]["addr_info"]
        if item["family"] == "inet"
    } == {(GUEST, 24)}
    request(SHARED, GUEST)
    if expected == "allow":
        request(INSIDE, GUEST)
        ping(INSIDE, "wlan0", 3)
    else:
        for _ in range(3):
            try:
                request(INSIDE, GUEST)
            except OSError as error:
                explicit_denial(error)
            else:
                raise AssertionError("The guest reached the protected internal endpoint")
            associated()
            time.sleep(2)
        ping(INSIDE, "wlan0", 0)
    request(SHARED, GUEST)
    associated()
    return {
        "status": "passed",
        "role": kind,
        "inside_access": expected,
        "shared_endpoint": "healthy",
        "associated": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("configure", "serve", "policy-on", "policy-off", "check")
    )
    parser.add_argument("--expect", choices=("deny", "allow"), default="deny")
    parser.add_argument("--policy", choices=("on", "off"), default="on")
    args = parser.parse_args()
    if os.geteuid() != 0 or (ROOT / "CML-WIRELESS-FIXTURE").read_text().strip() != radio.MARKER:
        raise PermissionError("Only marked disposable guest-policy nodes are accepted")
    kind = role()
    if args.action.startswith("policy-"):
        if kind != "ap":
            raise PermissionError("Only the AP may alter its forwarding policy")
        result = policy(args.action == "policy-on")
    elif args.action == "serve":
        with make_server((SHARED if kind == "ap" else INSIDE, 8080), kind) as server:
            server.serve_forever()
        return
    elif args.action == "configure":
        result = configure(kind)
    else:
        result = check(kind, args.expect, args.policy == "on")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
