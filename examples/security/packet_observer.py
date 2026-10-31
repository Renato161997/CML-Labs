"""Bounded receive-only witness for an isolated CML SPAN fixture."""

import argparse
import hashlib
import ipaddress
import json
import os
import select
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

PCAP = struct.Struct("<IHHIIII")
PACKET = struct.Struct("<IIII")
BENCH = ipaddress.ip_network("198.18.0.0/15")


def address(value):
    result = ipaddress.IPv4Address(value)
    if result not in BENCH:
        raise ValueError("Only isolated benchmark fixture addresses are permitted")
    return str(result)


def frame_facts(frame):
    if len(frame) < 14:
        return None
    offset = 14
    kind = int.from_bytes(frame[12:14], "big")
    for _ in range(2):
        if kind not in (0x8100, 0x88A8):
            break
        if len(frame) < offset + 4:
            return None
        kind = int.from_bytes(frame[offset + 2 : offset + 4], "big")
        offset += 4
    if kind != 0x0800 or len(frame) < offset + 20:
        return None
    ip = frame[offset:]
    ihl = (ip[0] & 15) * 4
    total = int.from_bytes(ip[2:4], "big")
    fragmented = int.from_bytes(ip[6:8], "big") & 0x3FFF
    if (
        ip[0] >> 4 != 4
        or ihl < 20
        or total < ihl + 20
        or total > len(ip)
        or fragmented
        or ip[9] != 6
    ):
        return None
    tcp = ip[ihl:total]
    header = (tcp[12] >> 4) * 4
    if header < 20 or header > len(tcp) or not tcp[header:].startswith(b"GET "):
        return None
    return {
        "source": str(ipaddress.IPv4Address(ip[12:16])),
        "destination": str(ipaddress.IPv4Address(ip[16:20])),
        "source_port": int.from_bytes(tcp[:2], "big"),
        "destination_port": int.from_bytes(tcp[2:4], "big"),
        "tos": ip[1],
        "frame_sha256": hashlib.sha256(frame).hexdigest(),
        "frame_bytes": len(frame),
    }


def pcap_bytes(frame, stamp):
    seconds = int(stamp)
    microseconds = int((stamp - seconds) * 1000000)
    return (
        PCAP.pack(0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
        + PACKET.pack(seconds, microseconds, len(frame), len(frame))
        + frame
    )


def pcap_frame(data):
    if len(data) < 40 or len(data) > 65575:
        raise ValueError("Invalid bounded fixture PCAP length")
    magic, major, minor, zone, sigfigs, snaplen, linktype = PCAP.unpack(data[:24])
    if (magic, major, minor, zone, sigfigs, snaplen, linktype) != (
        0xA1B2C3D4,
        2,
        4,
        0,
        0,
        65535,
        1,
    ):
        raise ValueError("Expected one Ethernet fixture PCAP")
    _seconds, micros, captured, original = PACKET.unpack(data[24:40])
    if micros >= 1000000 or captured != original or captured != len(data) - 40:
        raise ValueError("Truncated or inconsistent fixture PCAP")
    return data[40:]


def save(path, state):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def state_path(directory, phase):
    if phase not in ("p0", "p1", "p2", "p3", "p4"):
        raise ValueError("Unknown bounded phase")
    return directory / ("capture-" + phase + ".json")


def read_state(directory, phase):
    try:
        return json.loads(state_path(directory, phase).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def verdict(directory, phase):
    state = read_state(directory, phase)
    observed = False
    facts = None
    if state.get("ready") and state.get("finished") and state.get("captured"):
        try:
            frame = pcap_frame((directory / ("capture-" + phase + ".pcap")).read_bytes())
            facts = frame_facts(frame)
            observed = bool(
                facts
                and all(facts[k] == state[k] for k in ("source", "destination", "destination_port"))
                and facts["frame_sha256"] == state.get("frame_sha256")
            )
        except (OSError, ValueError, KeyError):
            pass
    quiet = bool(
        state.get("ready")
        and state.get("finished")
        and not state.get("captured")
        and state.get("elapsed", 0) >= state.get("window", 12)
        and state.get("window", 0) >= 12
    )
    return {
        "observed": observed,
        "quiet": quiet,
        "phase": phase,
        "packet": facts if observed else None,
        "frames_seen": state.get("frames_seen", 0),
        "get_candidates": state.get("get_candidates", 0),
    }


def listen(directory, phase, port, source, destination):
    if sys.platform != "linux" or os.geteuid() != 0:
        raise RuntimeError("Capture is restricted to an owned Linux fixture root guest")
    index = socket.if_nametoindex("eth1")
    flags = int(Path("/sys/class/net/eth1/flags").read_text().strip(), 16)
    if not flags & 1:
        raise RuntimeError("Fixture data interface is down")
    state = {
        "pid": os.getpid(),
        "phase": phase,
        "source": source,
        "destination": destination,
        "destination_port": port,
        "window": 12,
        "frames_seen": 0,
        "get_candidates": 0,
        "ready": False,
        "finished": False,
        "captured": False,
    }
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as receiver:
        receiver.bind(("eth1", 3))
        receiver.setsockopt(263, 1, struct.pack("=IHH8s", index, 1, 0, b""))
        started = time.monotonic()
        state["ready"] = True
        save(state_path(directory, phase), state)
        while time.monotonic() - started < 12:
            if not select.select([receiver], [], [], 0.1)[0]:
                continue
            frame = receiver.recv(65535)
            state["frames_seen"] += 1
            facts = frame_facts(frame)
            state["get_candidates"] += int(facts is not None)
            if not facts or any(
                facts[k] != state[k] for k in ("source", "destination", "destination_port")
            ):
                continue
            (directory / ("capture-" + phase + ".pcap")).write_bytes(pcap_bytes(frame, time.time()))
            state.update(captured=True, frame_sha256=facts["frame_sha256"])
            break
        state.update(finished=True, elapsed=time.monotonic() - started)
        save(state_path(directory, phase), state)


def arm(directory, phase, port, source, destination):
    directory.mkdir(parents=True, exist_ok=True)
    path = state_path(directory, phase)
    save(path, {"ready": False, "finished": False, "captured": False})
    (directory / ("capture-" + phase + ".pcap")).unlink(missing_ok=True)
    with (directory / ("capture-" + phase + ".log")).open("wb") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "listen",
                phase,
                str(port),
                "--source",
                source,
                "--destination",
                destination,
                "--directory",
                str(directory),
            ],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            close_fds=True,
            start_new_session=True,
        )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = read_state(directory, phase)
        if state.get("ready") and state.get("pid") == process.pid:
            return {"armed": True, "phase": phase}
        if process.poll() is not None:
            return {"armed": False, "phase": phase}
        time.sleep(0.05)
    process.terminate()
    process.wait(timeout=3)
    return {"armed": False, "phase": phase}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("arm", "listen", "proof"))
    parser.add_argument("phase", choices=("p0", "p1", "p2", "p3", "p4"))
    parser.add_argument(
        "port", type=int, nargs="?", choices=(8080, 8081, 8082, 8083, 8084), default=8080
    )
    parser.add_argument("--source", type=address, default="198.18.0.10")
    parser.add_argument("--destination", type=address, default="198.18.0.20")
    parser.add_argument("--directory", type=Path, default=Path("/lab"))
    parser.add_argument("--routed", action="store_true")
    args = parser.parse_args()
    if args.routed:
        args.source, args.destination = "198.18.10.10", "198.18.20.20"
    if args.action == "proof":
        result = verdict(args.directory, args.phase)
    elif args.action == "arm":
        result = arm(args.directory, args.phase, args.port, args.source, args.destination)
    else:
        listen(args.directory, args.phase, args.port, args.source, args.destination)
        return
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
