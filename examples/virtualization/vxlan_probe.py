"""Owned Linux VXLAN dataplane with real underlay, overlay and wire evidence."""

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
MARKER = "CML-VXLAN-DATAPLANE-V1"
DATA_LEFT, DATA_RIGHT = "198.19.0.1", "198.19.0.2"


def run(args, check=True):
    try:
        return subprocess.run(
            args,
            check=check,
            capture_output=True,
            text=True,
            timeout=15,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "LC_ALL": "C"},
        )
    except subprocess.CalledProcessError as error:
        error.add_note("Owned guest command stderr: " + (error.stderr or "")[:600])
        raise


def read(args):
    return json.loads(run(args).stdout)


def save(path, value):
    temporary = path.with_suffix(".next")
    temporary.write_text(json.dumps(value, sort_keys=True))
    temporary.replace(path)


def config():
    label = (ROOT / "vxlan-role").read_text().strip()
    mode = (ROOT / "vxlan-mode").read_text().strip()
    assert label in ("VTEP1", "VTEP2", "LEFT", "RIGHT") and mode in ("direct", "routed")
    second = "198.18.1.2" if mode == "routed" else "198.18.0.2"
    local, peer = ("198.18.0.1", second) if label == "VTEP1" else (second, "198.18.0.1")
    gateway = None if mode == "direct" else ("198.18.0.2" if label == "VTEP1" else "198.18.1.1")
    return {"role": label, "mode": mode, "local": local, "peer": peer, "gateway": gateway}


def vxlan_add(cfg, vni):
    assert cfg["role"] in ("VTEP1", "VTEP2") and vni in (100, 101)
    run(
        [
            "ip",
            "link",
            "add",
            "vx0",
            "type",
            "vxlan",
            "id",
            str(vni),
            "local",
            cfg["local"],
            "remote",
            cfg["peer"],
            "dev",
            "eth1",
            "dstport",
            "4789",
            "ttl",
            "64",
            "nolearning",
        ]
    )
    run(["ip", "link", "set", "vx0", "master", "br0"])
    run(["ip", "link", "set", "vx0", "up"])


def configure(cfg):
    if cfg["role"] in ("LEFT", "RIGHT"):
        address = DATA_LEFT if cfg["role"] == "LEFT" else DATA_RIGHT
        run(["ip", "link", "set", "eth1", "up"])
        run(["ip", "address", "add", address + "/30", "dev", "eth1"])
    else:
        run(["ip", "address", "add", cfg["local"] + "/30", "dev", "eth1"])
        run(["ip", "link", "set", "eth1", "up"])
        if cfg["gateway"]:
            prefix = str(ipaddress.IPv4Network(cfg["peer"] + "/30", strict=False))
            run(["ip", "route", "add", prefix, "via", cfg["gateway"], "dev", "eth1"])
        run(["ip", "link", "add", "br0", "type", "bridge"])
        run(["ip", "link", "set", "br0", "up"])
        run(["ip", "link", "set", "eth2", "up"])
        run(["ip", "link", "set", "eth2", "master", "br0"])
        vxlan_add(cfg, 100)
        if cfg["role"] == "VTEP2":
            save(ROOT / "vxlan-window.json", {"generation": 0})
    return {"status": "passed", "configured": cfg["role"], "mode": cfg["mode"]}


def state(cfg, expected=None):
    assert cfg["role"] in ("VTEP1", "VTEP2")
    link = read(["ip", "-d", "-j", "link", "show", "vx0"])[0]
    value = link["linkinfo"]["info_data"]
    assert link["linkinfo"]["info_kind"] == "vxlan" and value["id"] in (100, 101)
    assert "UP" in link["flags"] and link.get("master") == "br0"
    assert value["local"] == cfg["local"] and value["remote"] == cfg["peer"]
    assert value["port"] == 4789 and value["ttl"] == 64
    if expected is not None:
        assert value["id"] == expected
    address = read(["ip", "-j", "address", "show", "dev", "eth1"])[0]
    assert [entry["local"] for entry in address["addr_info"] if entry["family"] == "inet"] == [
        cfg["local"]
    ]
    route = read(["ip", "-j", "route", "get", cfg["peer"]])[0]
    assert route["dev"] == "eth1" and route.get("gateway") == cfg["gateway"]
    ports = read(["bridge", "-j", "link", "show"])
    for port in ("eth2", "vx0"):
        entry = next(row for row in ports if row["ifname"] == port)
        assert entry["state"] == "forwarding" and entry.get("master") == "br0"
    return {
        "status": "passed",
        "vni": value["id"],
        "mode": cfg["mode"],
        "kernel_release": os.uname().release,
    }


def change(cfg, vni):
    assert cfg["role"] == "VTEP2" and vni in (100, 101)
    before = state(cfg)
    if before["vni"] != vni:
        run(["ip", "link", "del", "vx0"])
        vxlan_add(cfg, vni)
    return state(cfg, vni)


def ping(interface, address, received):
    run(["ping", "-I", interface, "-c", "1", "-W", "1", address], False)
    value = run(["ping", "-I", interface, "-c", "3", "-i", "0.2", "-W", "1", address], False)
    match = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received", value.stdout)
    assert match and (int(match[1]), int(match[2])) == (3, received)
    assert value.returncode == (0 if received else 1)


def underlay(cfg):
    state(cfg)
    ping("eth1", cfg["peer"], 3)
    return {"status": "passed", "underlay_replies": 3, "mode": cfg["mode"]}


def overlay(cfg, up):
    assert cfg["role"] in ("LEFT", "RIGHT") and type(up) is bool
    own, target = (DATA_LEFT, DATA_RIGHT) if cfg["role"] == "LEFT" else (DATA_RIGHT, DATA_LEFT)
    address = read(["ip", "-j", "address", "show", "dev", "eth1"])[0]
    assert "UP" in address["flags"]
    assert [entry["local"] for entry in address["addr_info"] if entry["family"] == "inet"] == [own]
    ping("eth1", target, 3 if up else 0)
    return {"status": "passed", "overlay_replies": 3 if up else 0}


def ipv4(packet):
    if len(packet) < 20 or packet[0] >> 4 != 4:
        raise ValueError("Invalid IPv4 header")
    header = (packet[0] & 15) * 4
    size = struct.unpack("!H", packet[2:4])[0]
    if (
        header < 20
        or not header <= size <= len(packet)
        or struct.unpack("!H", packet[6:8])[0] & 0x3FFF
    ):
        raise ValueError("Truncated or fragmented packet outside the small-probe scope")
    return (
        header,
        size,
        str(ipaddress.IPv4Address(packet[12:16])),
        str(ipaddress.IPv4Address(packet[16:20])),
    )


def inspect(frame, peer, local):
    frame = bytes(frame)
    if len(frame) < 14 or frame[12:14] != b"\x08\x00":
        return None
    outer = frame[14:]
    header, size, source, target = ipv4(outer)
    if outer[9] != 17 or (source, target) != (peer, local):
        return None
    udp = outer[header:size]
    if len(udp) < 8 or struct.unpack("!H", udp[2:4])[0] != 4789:
        return None
    if len(udp) < 30 or struct.unpack("!H", udp[4:6])[0] != len(udp):
        raise ValueError("Invalid UDP framing")
    vx = udp[8:16]
    if vx[:4] != b"\x08\0\0\0" or vx[7] != 0:
        raise ValueError("Only the declared basic VXLAN I-flag is supported")
    vni = int.from_bytes(vx[4:7], "big")
    if not vni:
        raise ValueError("Unexpected zero VNI")
    inner = udp[16:]
    if len(inner) < 14:
        raise ValueError("Truncated inner Ethernet frame")
    packet, kind = inner[14:], None
    if inner[12:14] == b"\x08\x06":
        if len(packet) < 28 or packet[:8] != b"\0\x01\x08\0\x06\x04\0\x01":
            return None
        if (
            str(ipaddress.IPv4Address(packet[14:18])),
            str(ipaddress.IPv4Address(packet[24:28])),
        ) == (DATA_LEFT, DATA_RIGHT):
            kind = "arp-request"
    elif inner[12:14] == b"\x08\x00":
        ih, total, src, dst = ipv4(packet)
        if (
            packet[9] == 1
            and (src, dst) == (DATA_LEFT, DATA_RIGHT)
            and total >= ih + 8
            and packet[ih] == 8
            and packet[ih + 1] == 0
        ):
            kind = "echo-request"
    return {"vni": vni, "ttl": outer[8], "kind": kind} if kind else None


def serve(cfg):
    assert cfg["role"] == "VTEP2"
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as receiver:
        receiver.bind(("eth1", 0))
        generation = -1
        while True:
            requested = json.loads((ROOT / "vxlan-window.json").read_text())["generation"]
            if requested != generation:
                generation = requested
                count, errors, vnis, ttls, kinds = 0, 0, set(), set(), set()
            if select.select([receiver], [], [], 0.2)[0]:
                raw, address = receiver.recvfrom(65535)
                if address[2] == socket.PACKET_OUTGOING:
                    continue
                try:
                    value = inspect(raw, cfg["peer"], cfg["local"])
                    if value:
                        count += 1
                        vnis.add(value["vni"])
                        ttls.add(value["ttl"])
                        kinds.add(value["kind"])
                except ValueError:
                    errors += 1
            save(
                ROOT / "vxlan-counters.json",
                {
                    "pid": os.getpid(),
                    "generation": generation,
                    "selected_packets": count,
                    "parse_errors": errors,
                    "vnis": sorted(vnis),
                    "ttls": sorted(ttls),
                    "kinds": sorted(kinds),
                },
            )


def worker():
    path = ROOT / "vxlan-capture.pid"
    if not path.exists():
        return None
    pid = int(path.read_text())
    assert pid > 1
    process = Path("/proc") / str(pid)
    if not process.exists():
        return None
    command = (process / "cmdline").read_bytes().split(b"\0")
    assert (
        len(command) >= 3
        and command[1] == str(Path(__file__).resolve()).encode()
        and command[2] == b"serve"
    )
    return pid


def capture(cfg):
    assert cfg["role"] == "VTEP2"
    pid = worker()
    if pid is None:
        with (ROOT / "vxlan-capture.log").open("ab") as output:
            child = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "serve"],
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        pid = child.pid
        (ROOT / "vxlan-capture.pid").write_text(str(pid))
    window = json.loads((ROOT / "vxlan-window.json").read_text())
    generation = window["generation"] + 1
    save(ROOT / "vxlan-window.json", {"generation": generation})
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        path = ROOT / "vxlan-counters.json"
        if path.exists():
            value = json.loads(path.read_text())
            if value["pid"] == pid and value["generation"] == generation:
                return {"status": "passed", "capture_generation": generation}
        time.sleep(0.2)
    raise TimeoutError("Owned capture did not acknowledge its new evidence window")


def evidence(cfg, mismatch):
    assert cfg["role"] == "VTEP2"
    actual = state(cfg, 101 if mismatch else 100)
    value = json.loads((ROOT / "vxlan-counters.json").read_text())
    assert (
        value["pid"] == worker()
        and value["generation"]
        == json.loads((ROOT / "vxlan-window.json").read_text())["generation"]
    )
    assert value["selected_packets"] >= 1 and value["parse_errors"] == 0
    assert value["vnis"] == [100] and value["ttls"] == [63 if cfg["mode"] == "routed" else 64]
    assert bool(actual["vni"] != value["vnis"][0]) == mismatch
    return {
        "status": "passed",
        "receiver_vni": actual["vni"],
        "wire_vni": 100,
        "wire_ttl": value["ttls"][0],
        "selected_packets": value["selected_packets"],
        "vni_mismatch": mismatch,
        "generation": value["generation"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "configure",
            "state",
            "underlay",
            "good",
            "down",
            "mismatch",
            "repair",
            "capture",
            "serve",
            "wire-good",
            "wire-mismatch",
        ),
    )
    action = parser.parse_args().action
    if os.geteuid() != 0 or (ROOT / "CML-VXLAN-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the marked isolated VXLAN fixture is accepted")
    cfg = config()
    if action == "configure":
        value = configure(cfg)
    elif action == "state":
        value = state(cfg)
    elif action == "underlay":
        value = underlay(cfg)
    elif action in ("good", "down"):
        value = overlay(cfg, action == "good")
    elif action in ("mismatch", "repair"):
        value = change(cfg, 101 if action == "mismatch" else 100)
    elif action == "capture":
        value = capture(cfg)
    elif action == "serve":
        serve(cfg)
        return
    else:
        value = evidence(cfg, action == "wire-mismatch")
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
