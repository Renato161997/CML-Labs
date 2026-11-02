"""Disposable live raw-Ethernet first-hop peers and inspector; fixed lab links only."""

import argparse
import json
import os
import re
import secrets
import select
import socket
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path

import first_hop_policy as policy
import first_hop_wire as wire

ROOT = Path("/lab")
BAD_MAC = bytes.fromhex("020000000066")


def run(args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
    if check and result.returncode:
        raise RuntimeError("Fixture command failed: " + args[0])
    return result


def role():
    value = (ROOT / "firsthop-role").read_text().strip()
    assert value in ("GUARD", "CLIENT", "SERVER")
    return value


def write(path, value):
    assert not path.is_symlink()
    temporary = path.with_suffix(path.suffix + ".next")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True)
    temporary.chmod(0o600)
    temporary.replace(path)


def mac(nic):
    return bytes.fromhex(
        Path("/sys/class/net", nic, "address").read_text().strip().replace(":", "")
    )


def spawn(name, args):
    assert not (ROOT / (name + ".pid")).exists()
    with (ROOT / (name + ".log")).open("wb") as log:
        child = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    write(ROOT / (name + ".pid"), child.pid)


def alive(name, action):
    path = ROOT / (name + ".pid")
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0 and metadata.st_nlink == 1
    pid = json.loads(path.read_text())
    assert type(pid) is int and pid > 1
    try:
        args = Path("/proc", str(pid), "cmdline").read_bytes().split(b"\0")
    except (FileNotFoundError, ProcessLookupError):
        return False
    return b"/lab/h.py" in args and action.encode() in args


def channel(nic):
    result = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    result.bind((nic, 0))
    return result


def configure():
    who = role()
    if who == "CLIENT":
        run(["ip", "link", "set", "eth1", "down"])
        run(["ip", "link", "set", "eth1", "address", wire.CLIENT_MAC.hex(":")])
    for nic in ("eth1", "eth2") if who == "GUARD" else ("eth1",):
        run(["ip", "link", "set", nic, "up"])
    if who == "GUARD":
        for nic in ("eth1", "eth2"):
            run(["ip", "link", "set", nic, "promisc", "on"])
        run(["ip", "addr", "add", "198.18.99.1/30", "dev", "eth3"])
        run(["ip", "link", "set", "eth3", "up"])
        run(["ip", "route", "add", "unreachable", "198.18.10.0/24"])
        spawn("inspector", [sys.executable, "/lab/h.py", "worker"])
    elif who == "CLIENT":
        run(["ip", "addr", "add", "198.18.99.2/30", "dev", "eth2"])
        run(["ip", "link", "set", "eth2", "up"])
    else:
        run(["ip", "addr", "add", wire.SERVER + "/24", "dev", "eth1"])
        write(ROOT / "server-lease.json", 600)
        spawn("dhcp", [sys.executable, "/lab/h.py", "server"])
        spawn(
            "http",
            [sys.executable, "/lab/t.py", "serve", wire.SERVER, "--label", "OUTSIDE"],
        )
    return {"status": "passed", "configured": who}


def worker():
    assert role() == "GUARD"
    gate = policy.Gate()
    sockets = {channel("eth1"): 1, channel("eth2"): 2}
    outputs = {side: sock for sock, side in sockets.items()}
    while True:
        ready, _, _ = select.select(list(sockets), [], [], 0.1)
        for source in ready:
            frame, address = source.recvfrom(4096)
            if address[2] == 4:  # PACKET_OUTGOING: do not inspect our own forwarding copy.
                continue
            side = sockets[source]
            if gate.process(side, frame, time.monotonic()):
                outputs[3 - side].send(frame)
        now = time.monotonic()
        write(ROOT / "inspection.json", {**gate.snapshot(now), "written_at": now})


def server():
    assert role() == "SERVER"
    sock = channel("eth1")
    pending = None
    counts = {"offers": 0, "acks": 0}
    while True:
        frame, address = sock.recvfrom(4096)
        if address[2] == 4:
            continue
        try:
            value = wire.dhcp(frame)
        except ValueError:
            continue
        if (
            value["message"] not in (1, 3)
            or value["src_mac"] != value["client_mac"]
            or value["client_mac"] != wire.CLIENT_MAC
        ):
            continue
        now = time.monotonic()
        if value["message"] == 1:
            lease = json.loads((ROOT / "server-lease.json").read_text())
            assert lease in (3, 600)
            pending = {"xid": value["xid"], "lease": lease, "expires": now + 20}
            sock.send(wire.make_dhcp(2, value["xid"], mac("eth1"), lease=lease))
            counts["offers"] += 1
        elif pending is not None and now < pending["expires"] and value["xid"] == pending["xid"]:
            sock.send(wire.make_dhcp(5, value["xid"], mac("eth1"), lease=pending["lease"]))
            counts["acks"] += 1
        write(ROOT / "server-state.json", {**counts, "written_at": now})


def receive(sock, message, xid, deadline):
    while time.monotonic() < deadline:
        ready, _, _ = select.select([sock], [], [], min(0.5, max(0, deadline - time.monotonic())))
        if not ready:
            continue
        frame, address = sock.recvfrom(4096)
        if address[2] == 4:
            continue
        try:
            value = wire.dhcp(frame)
        except ValueError:
            continue
        if (
            value["message"] == message
            and value["xid"] == xid
            and value["client_mac"] == wire.CLIENT_MAC
        ):
            return value
    raise TimeoutError("No matching actual DHCP peer response")


def address_present(value):
    rows = json.loads(run(["ip", "-j", "addr", "show", "dev", "eth1"]).stdout)
    return any(
        a.get("local") == value and a.get("prefixlen") == 24
        for row in rows
        for a in row.get("addr_info", [])
    )


def acquire():
    assert role() == "CLIENT" and mac("eth1") == wire.CLIENT_MAC
    for attempt in range(3):
        with channel("eth1") as sock:
            xid = secrets.randbits(32)
            sock.send(wire.make_dhcp(1, xid, wire.CLIENT_MAC))
            try:
                offer = receive(sock, 2, xid, time.monotonic() + 4)
                sock.send(wire.make_dhcp(3, xid, wire.CLIENT_MAC))
                ack = receive(sock, 5, xid, time.monotonic() + 4)
                assert ack["lease"] == offer["lease"] and ack["src_mac"] == offer["src_mac"]
                break
            except TimeoutError:
                if attempt == 2:
                    raise
    run(["ip", "addr", "replace", ack["offered"] + "/24", "dev", "eth1"])
    assert address_present(wire.LEASED)
    write(
        ROOT / "last-ack.json",
        {"xid": xid, "lease": ack["lease"], "server_mac": ack["src_mac"].hex(":")},
    )
    return {
        "status": "passed",
        "actual_dhcp_ack": True,
        "xid_matched": True,
        "kernel_address_confirmed": True,
        "lease": ack["lease"],
    }


def ping(source=None):
    args = ["ping", "-n", "-c", "3", "-W", "1"]
    if source is not None:
        args += ["-I", source]
    result = run([*args, wire.SERVER], check=False)
    match = re.search(r"3 packets transmitted, ([0-3]) received", result.stdout)
    if match is None:
        raise ValueError("Incomplete independent packet observation")
    return int(match[1])


def data_good():
    deadline, consecutive = time.monotonic() + 15, 0
    while True:
        received = ping()
        if time.monotonic() > deadline:
            raise AssertionError("Authorized real data did not stabilize")
        consecutive = consecutive + 1 if received == 3 else 0
        if consecutive == 2:
            return {
                "status": "passed",
                "phase": "data-good",
                "consecutive_complete_trains": 2,
            }
        time.sleep(0.25)


def control_no_bypass():
    run(["ip", "route", "add", wire.SERVER + "/32", "via", "198.18.99.1", "dev", "eth2"])
    try:
        assert ping(source=wire.LEASED) == 0
    finally:
        run(
            [
                "ip",
                "route",
                "del",
                wire.SERVER + "/32",
                "via",
                "198.18.99.1",
                "dev",
                "eth2",
            ]
        )
    data_good()
    return {
        "status": "passed",
        "phase": "control-no-bypass",
        "blocked": True,
        "normal_data_recovered": True,
    }


def rogue():
    saved = json.loads((ROOT / "last-ack.json").read_text())
    with channel("eth1") as sock:
        frame = wire.make_dhcp(5, saved["xid"], wire.CLIENT_MAC, lease=600)
        for _ in range(3):
            sock.send(frame)
            time.sleep(0.1)
    return {"status": "passed", "phase": "rogue", "valid_rogue_ack_frames_sent": 3}


def arp_spoof():
    saved = json.loads((ROOT / "last-ack.json").read_text())
    target = bytes.fromhex(saved["server_mac"].replace(":", ""))
    body = (
        struct.pack("!HHBBH", 1, 0x0800, 6, 4, 2)
        + BAD_MAC
        + wire.ip_bytes(wire.LEASED)
        + target
        + wire.ip_bytes(wire.SERVER)
    )
    frame = (target + BAD_MAC + b"\x08\x06" + body).ljust(60, b"\0")
    assert wire.arp(frame)["src_mac"] == BAD_MAC
    with channel("eth1") as sock:
        for _ in range(3):
            sock.send(frame)
            time.sleep(0.1)
    return {
        "status": "passed",
        "phase": "arp-spoof",
        "coherent_spoofed_arp_replies_sent": 3,
    }


def spoof_ip():
    run(["ip", "addr", "add", "198.18.10.11/24", "dev", "eth1"])
    try:
        assert ping(source="198.18.10.11") == 0
    finally:
        run(["ip", "addr", "del", "198.18.10.11/24", "dev", "eth1"])
    assert not address_present("198.18.10.11") and address_present(wire.LEASED)
    return {
        "status": "passed",
        "phase": "spoof-ip",
        "actual_spoofed_source_received": 0,
        "secondary_address_removed": True,
    }


def kernel_boundary():
    routes = json.loads(run(["ip", "-j", "route", "show", "exact", "198.18.10.0/24"]).stdout)
    assert any(
        row.get("type") == "unreachable" and row.get("dst") == "198.18.10.0/24" for row in routes
    )
    for nic in ("eth1", "eth2"):
        links = json.loads(run(["ip", "-j", "link", "show", "dev", nic]).stdout)
        assert len(links) == 1 and "master" not in links[0], (
            "A kernel bridge could bypass inspection"
        )
        addresses = json.loads(run(["ip", "-j", "addr", "show", "dev", nic]).stdout)
        assert not any(
            a.get("family") == "inet" for row in addresses for a in row.get("addr_info", [])
        )


def guard_report(phase):
    assert role() == "GUARD" and alive("inspector", "worker")
    kernel_boundary()
    value = json.loads((ROOT / "inspection.json").read_text())
    assert 0 <= time.monotonic() - value["written_at"] <= 3
    binding = value["binding"]
    if phase == "expired":
        assert (
            binding is None and value["last_lease"] == 3 and value["counts"]["lease_expired"] >= 1
        )
    else:
        assert (
            binding is not None
            and binding["mac"] == wire.CLIENT_MAC.hex(":")
            and binding["ip"] == wire.LEASED
            and binding["port"] == 1
            and binding["remaining"] > 0
        )
        assert binding["lease"] == 600
        if phase == "rogue-blocked":
            assert value["counts"]["untrusted_server_drop"] >= 3
        elif phase == "arp-blocked":
            assert value["counts"]["arp_binding_drop"] >= 3
        elif phase == "ip-blocked":
            assert value["counts"]["ip_binding_drop"] >= 3
        elif phase == "recovered":
            assert value["counts"]["ack_learned"] >= 3 and value["counts"]["lease_expired"] >= 1
        else:
            assert phase == "bound" and value["counts"]["ack_learned"] >= 1
    return {
        "status": "passed",
        "phase": phase,
        "actual_worker_alive": True,
        "kernel_bypass_blocked": True,
        **value,
    }


def neighbor_safe():
    assert role() == "SERVER" and alive("dhcp", "server")
    rows = json.loads(run(["ip", "-j", "neigh", "show", "to", wire.LEASED, "dev", "eth1"]).stdout)
    assert any(row.get("lladdr") == wire.CLIENT_MAC.hex(":") for row in rows)
    return {
        "status": "passed",
        "phase": "neighbor-safe",
        "actual_neighbor_mac": wire.CLIENT_MAC.hex(":"),
    }


def decode_wire():
    assert role() == "SERVER"
    frames = [
        wire.make_dhcp(kind, 0x12345678, mac("eth1") if kind in (2, 5) else wire.CLIENT_MAC)
        for kind in (1, 2, 3, 5)
    ]
    path = ROOT / "synthetic-dora.pcap"
    assert not path.is_symlink()
    path.write_bytes(wire.pcap(frames))
    result = run(["tcpdump", "-nn", "-vvv", "-r", str(path)])
    decoded = re.findall(r"DHCP-Message[^\n]*?:\s*(Discover|Offer|Request|ACK)", result.stdout)
    assert decoded == ["Discover", "Offer", "Request", "ACK"], (
        "Independent tcpdump did not decode the intended DORA wire profile"
    )
    assert "bad cksum" not in result.stdout.lower()
    return {
        "status": "passed",
        "phase": "decode-wire",
        "independent_decoder": "tcpdump",
        "decoded_messages": decoded,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "configure",
            "worker",
            "server",
            "acquire",
            "data-good",
            "expired-data",
            "control-no-bypass",
            "rogue",
            "arp-spoof",
            "spoof-ip",
            "bound",
            "rogue-blocked",
            "arp-blocked",
            "ip-blocked",
            "expired",
            "recovered",
            "neighbor-safe",
            "decode-wire",
            "short",
            "long",
        ),
    )
    args = parser.parse_args()
    assert os.geteuid() == 0 and (ROOT / "CML-FIRST-HOP").read_text().strip() == "CML-FIRST-HOP-V1"
    action = args.action
    if action == "configure":
        value = configure()
    elif action == "worker":
        worker()
        return
    elif action == "server":
        server()
        return
    elif action in ("short", "long"):
        assert role() == "SERVER"
        write(ROOT / "server-lease.json", 3 if action == "short" else 600)
        value = {"status": "passed", "lease_policy": 3 if action == "short" else 600}
    elif action in (
        "bound",
        "rogue-blocked",
        "arp-blocked",
        "ip-blocked",
        "expired",
        "recovered",
    ):
        value = guard_report(action)
    elif action == "neighbor-safe":
        value = neighbor_safe()
    elif action == "decode-wire":
        value = decode_wire()
    else:
        assert role() == "CLIENT"
        if action == "expired-data":
            time.sleep(5)
            assert address_present(wire.LEASED) and ping() == 0
            value = {
                "status": "passed",
                "phase": action,
                "stale_kernel_address_retained": True,
                "actual_received": 0,
            }
        else:
            value = {
                "acquire": acquire,
                "data-good": data_good,
                "control-no-bypass": control_no_bypass,
                "rogue": rogue,
                "arp-spoof": arp_spoof,
                "spoof-ip": spoof_ip,
            }[action]()
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
