"""Bounded classroom RA guard with actual frames and independent kernel routes."""

import argparse
import ipaddress
import json
import os
import re
import select
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-RA-GUARD-V1"
ROLES = {"ROUTER", "ROGUE", "CLIENT", "GUARD"}
PORTS = ("eth1", "eth2", "eth3")
GATEWAYS = {"trusted": "fe80::1", "rogue": "fe80::66"}


def run(argv, check=True):
    return subprocess.run(
        argv,
        check=check,
        capture_output=True,
        text=True,
        timeout=20,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "LC_ALL": "C"},
    )


def save(path, value):
    temporary = path.with_suffix(".next")
    temporary.write_text(json.dumps(value, sort_keys=True))
    temporary.replace(path)


def role():
    value = (ROOT / "ra-role").read_text().strip()
    if value not in ROLES:
        raise ValueError("Unexpected RA exercise role")
    return value


def checksum(data):
    if len(data) % 2:
        data += b"\0"
    value = sum(struct.unpack("!" + "H" * (len(data) // 2), data))
    while value >> 16:
        value = (value & 65535) + (value >> 16)
    return (~value) & 65535


def ra_frame(mac, gateway, high=False, extension=False):
    if len(mac) != 6 or mac[0] & 1 or gateway not in GATEWAYS.values():
        raise ValueError("Only the owned benchmark advertisers are accepted")
    source = ipaddress.IPv6Address(gateway).packed
    target = ipaddress.IPv6Address("ff02::1").packed
    message = (
        struct.pack("!BBHBBHII", 134, 0, 0, 64, 8 if high else 0, 1800, 0, 1000) + b"\x01\x01" + mac
    )
    pseudo = source + target + struct.pack("!I3xB", len(message), 58)
    message = message[:2] + struct.pack("!H", checksum(pseudo + message)) + message[4:]
    extra = b"\x3a\x00\x01\x04\0\0\0\0" if extension else b""
    header = struct.pack(
        "!IHBB16s16s",
        6 << 28,
        len(message) + len(extra),
        0 if extension else 58,
        255,
        source,
        target,
    )
    return b"\x33\x33\0\0\0\x01" + mac + b"\x86\xdd" + header + extra + message


def inspect(data):
    if len(data) < 14:
        raise ValueError("Truncated Ethernet frame")
    if data[12:14] in (b"\x81\0", b"\x88\xa8"):
        raise ValueError("This declared untagged fixture does not forward VLAN frames")
    if data[12:14] != b"\x86\xdd":
        return {"kind": "other"}
    if len(data) < 54 or data[14] >> 4 != 6:
        raise ValueError("Truncated or invalid IPv6 header")
    end = 54 + int.from_bytes(data[18:20], "big")
    if end > len(data):
        raise ValueError("Incomplete IPv6 payload")
    next_header, offset, extensions = data[20], 54, 0
    while next_header in (0, 43, 60):
        extensions += 1
        if extensions > 4 or offset + 2 > end:
            raise ValueError("Extension chain exceeds the bounded parser")
        following, size = data[offset], (data[offset + 1] + 1) * 8
        if offset + size > end:
            raise ValueError("Truncated extension header")
        next_header, offset = following, offset + size
    if next_header not in (6, 17, 58, 59):
        raise ValueError("Fragments or opaque/unsupported headers are outside the fixture")
    if next_header != 58:
        return {"kind": "other"}
    if offset + 4 > end:
        raise ValueError("Truncated ICMPv6 header")
    if data[offset] != 134:
        return {"kind": "other"}
    source, destination = data[22:38], data[38:54]
    message = data[offset:end]
    pseudo = source + destination + struct.pack("!I3xB", len(message), 58)
    if (
        len(message) < 16
        or message[1]
        or data[21] != 255
        or not ipaddress.IPv6Address(source).is_link_local
        or checksum(pseudo + message)
        or data[6] & 1
    ):
        raise ValueError("Invalid RA code, scope, hop limit or checksum")
    position = 16
    while position < len(message):
        if position + 2 > len(message) or not message[position + 1]:
            raise ValueError("Invalid ND option length")
        size = message[position + 1] * 8
        if position + size > len(message):
            raise ValueError("Truncated ND option")
        if message[position] == 1 and (
            size != 8 or message[position + 2 : position + 8] != data[6:12]
        ):
            raise ValueError("Source link-layer option disagrees with the actual frame")
        position += size
    return {
        "kind": "ra",
        "gateway": str(ipaddress.IPv6Address(source)),
        "extension": extensions > 0,
    }


def permitted(data, incoming, enabled):
    if incoming not in PORTS or type(enabled) is not bool:
        raise ValueError("Unknown policy port or state")
    info = inspect(data)
    allowed = (
        info["kind"] != "ra"
        or not enabled
        or (incoming == "eth1" and info["gateway"] == GATEWAYS["trusted"])
    )
    return allowed, info


def configuration():
    value = json.loads((ROOT / "ra-policy.json").read_text())
    if (
        set(value) != {"enabled", "generation"}
        or type(value["enabled"]) is not bool
        or type(value["generation"]) is not int
        or value["generation"] < 1
    ):
        raise ValueError("Invalid owned RA policy")
    return value


def serve():
    assert role() == "GUARD"
    sockets = []
    try:
        for port in PORTS:
            descriptor = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
            descriptor.bind((port, 0))
            sockets.append(descriptor)
        state, learned = None, {}
        while True:
            policy = configuration()
            if state is None or state["generation"] != policy["generation"]:
                state = {
                    **policy,
                    "blocked_ra": 0,
                    "forwarded_ra": 0,
                    "extension_ra": 0,
                    "malformed": 0,
                    "forwarded_other": 0,
                    "pid": os.getpid(),
                }
                save(ROOT / "ra-counters.json", state)
            ready, _, _ = select.select(sockets, [], [], 0.2)
            for descriptor in ready:
                data, address = descriptor.recvfrom(4096)
                if address[2] == socket.PACKET_OUTGOING:
                    continue
                incoming = PORTS[sockets.index(descriptor)]
                try:
                    allowed, info = permitted(data, incoming, policy["enabled"])
                except ValueError:
                    state["malformed"] += 1
                    save(ROOT / "ra-counters.json", state)
                    continue
                if info["kind"] == "ra":
                    state["forwarded_ra" if allowed else "blocked_ra"] += 1
                    state["extension_ra"] += int(info["extension"])
                if not allowed:
                    save(ROOT / "ra-counters.json", state)
                    continue
                learned[data[6:12]] = descriptor
                destination = learned.get(data[:6]) if not data[0] & 1 else None
                targets = [destination] if destination is not None else sockets
                for output in targets:
                    if output is not descriptor:
                        output.send(data)
                if info["kind"] != "ra":
                    state["forwarded_other"] += 1
                save(ROOT / "ra-counters.json", state)
    finally:
        for descriptor in sockets:
            descriptor.close()


def owned(pid):
    if type(pid) is not int or pid <= 1:
        raise ValueError("Unsafe guard PID")
    try:
        args = (Path("/proc") / str(pid) / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    except FileNotFoundError:
        return False
    return args == [os.fsencode(sys.executable), os.fsencode(Path(__file__).resolve()), b"serve"]


def start():
    path = ROOT / "ra-guard.pid"
    if path.exists() and owned(int(path.read_text())):
        return
    with (ROOT / "ra-guard.log").open("ab") as output:
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
        assert child.poll() is None, "Owned guard exited during startup"
        if (ROOT / "ra-counters.json").exists() and json.loads(
            (ROOT / "ra-counters.json").read_text()
        )["pid"] == child.pid:
            return
        time.sleep(0.2)
    raise TimeoutError("Owned guard did not become ready")


def configure(kind):
    if kind == "GUARD":
        for port in PORTS:
            for command in [
                ["ip", "link", "set", "dev", port, "addrgenmode", "none"],
                ["ip", "-6", "address", "flush", "dev", port],
                ["ip", "link", "set", "dev", port, "up"],
                ["ip", "link", "set", "dev", port, "promisc", "on"],
            ]:
                run(command)
        if not (ROOT / "ra-policy.json").exists():
            save(ROOT / "ra-policy.json", {"enabled": True, "generation": 1})
        start()
    else:
        interface = "ens2"
        suffix = {"CLIENT": "2", "ROUTER": "1", "ROGUE": "66"}[kind]
        run(["ip", "link", "set", "dev", interface, "addrgenmode", "none"])
        run(["ip", "-6", "address", "flush", "dev", interface])
        run(["ip", "link", "set", "dev", interface, "up"])
        for address in ("fe80::" + suffix, "2001:db8:1::" + suffix):
            run(["ip", "-6", "address", "add", address + "/64", "dev", interface, "nodad"])
        if kind in ("ROUTER", "ROGUE"):
            # These are owned Ubuntu VMs, not native containers with read-only sysctls.
            run(["sysctl", "-w", "net.ipv6.conf.all.forwarding=1"])
        if kind == "CLIENT":
            for name, value in (
                ("autoconf", 0),
                ("accept_ra", 2),
                ("accept_ra_defrtr", 1),
                ("accept_ra_rtr_pref", 1),
            ):
                run(["sysctl", "-w", "net.ipv6.conf." + interface + "." + name + "=" + str(value)])
    return {"configured": True, "role": kind}


def policy(enabled):
    assert role() == "GUARD" and type(enabled) is bool
    value = configuration()
    save(ROOT / "ra-policy.json", {"enabled": enabled, "generation": value["generation"] + 1})
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = json.loads((ROOT / "ra-counters.json").read_text())
        if state["generation"] == value["generation"] + 1 and state["enabled"] == enabled:
            return {"policy_enabled": enabled, "counters_reset": True}
        time.sleep(0.2)
    raise TimeoutError("Guard did not acknowledge the exact policy generation")


def advertise(kind, extension):
    assert kind in ("ROUTER", "ROGUE")
    value = json.loads(run(["ip", "-j", "link", "show", "ens2"]).stdout)[0]
    mac = bytes.fromhex(value["address"].replace(":", ""))
    frame = ra_frame(
        mac, GATEWAYS["trusted" if kind == "ROUTER" else "rogue"], kind == "ROGUE", extension
    )
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as transmitter:
        transmitter.bind(("ens2", 0))
        for _ in range(5):
            assert transmitter.send(frame) == len(frame)
            time.sleep(0.3)
    return {"advertised": 5, "role": kind, "extension": extension}


def routes(expected):
    assert role() == "CLIENT" and expected in GATEWAYS
    deadline = time.monotonic() + 20
    actual = []
    while time.monotonic() < deadline:
        result = run(["ip", "-j", "-6", "route", "get", "2001:db8:ffff::1"], False)
        if result.returncode == 0:
            actual = json.loads(result.stdout)
            if (
                len(actual) == 1
                and actual[0].get("gateway") == GATEWAYS[expected]
                and actual[0].get("dev") == "ens2"
            ):
                defaults = json.loads(
                    run(["ip", "-j", "-6", "route", "show", "default", "dev", "ens2"]).stdout
                )
                if expected == "trusted":
                    assert not any(item.get("gateway") == GATEWAYS["rogue"] for item in defaults), (
                        "An already learned rogue route must be explicitly removed"
                    )
                return {
                    "status": "passed",
                    "selected_gateway": GATEWAYS[expected],
                    "actual_kernel_routes": True,
                }
        time.sleep(0.5)
    raise AssertionError(
        {
            "expected_gateway": GATEWAYS[expected],
            "observed_route": actual,
            "defaults": run(["ip", "-j", "-6", "route", "show", "default"], False).stdout,
            "neighbors": run(["ip", "-j", "-6", "neigh", "show"], False).stdout,
            "network_manager": run(
                ["journalctl", "-u", "systemd-networkd", "-n", "12", "--no-pager"], False
            ).stdout,
        }
    )


def recover():
    assert role() == "CLIENT"
    rows = json.loads(run(["ip", "-j", "-6", "route", "show", "default", "dev", "ens2"]).stdout)
    removed = 0
    for item in rows:
        if item.get("gateway") == GATEWAYS["rogue"]:
            assert item.get("protocol") == "ra", (
                "Refuse to remove a route outside the learned RA scope"
            )
            run(
                [
                    "ip",
                    "-6",
                    "route",
                    "del",
                    "default",
                    "via",
                    GATEWAYS["rogue"],
                    "dev",
                    "ens2",
                    "proto",
                    "ra",
                ]
            )
            removed += 1
    assert removed == 1, "Recovery must remove the actual previously learned rogue route"
    return {**routes("trusted"), "rogue_removed": removed}


def health():
    assert role() == "CLIENT"
    for target in ("2001:db8:1::1", "2001:db8:1::66"):
        result = run(["ping", "-6", "-I", "ens2", "-c", "3", "-W", "2", target], False)
        counts = re.search(r"(\d+) (?:packets )?transmitted, (\d+) received", result.stdout)
        assert result.returncode == 0 and counts and (int(counts[1]), int(counts[2])) == (3, 3), (
            "Both trusted and untrusted ports must retain actual IPv6 data forwarding"
        )
    return {"status": "passed", "ipv6_data_replies": 6}


def evidence(blocked):
    assert role() == "GUARD"
    value = json.loads((ROOT / "ra-counters.json").read_text())
    assert value["generation"] == configuration()["generation"] and value["enabled"] == blocked
    assert value["blocked_ra" if blocked else "forwarded_ra"] >= 5
    assert value["extension_ra"] >= 5
    return {
        "status": "passed",
        "blocked": blocked,
        "ra_packets": value["blocked_ra" if blocked else "forwarded_ra"],
        "extension_packets": value["extension_ra"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "configure",
            "serve",
            "advertise",
            "policy-on",
            "policy-off",
            "reset",
            "trusted",
            "rogue",
            "recover",
            "health",
            "blocked",
            "forwarded",
        ),
    )
    parser.add_argument("--extension", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0 or (ROOT / "CML-RA-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only marked disposable RA exercise nodes are accepted")
    kind = role()
    if args.action == "serve":
        serve()
        return
    if args.action == "configure":
        result = configure(kind)
    elif args.action == "advertise":
        result = advertise(kind, args.extension)
    elif args.action.startswith("policy-") or args.action == "reset":
        result = policy(
            configuration()["enabled"] if args.action == "reset" else args.action == "policy-on"
        )
    elif args.action in GATEWAYS:
        result = routes(args.action)
    elif args.action == "recover":
        result = recover()
    elif args.action == "health":
        result = health()
    else:
        result = evidence(args.action == "blocked")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
