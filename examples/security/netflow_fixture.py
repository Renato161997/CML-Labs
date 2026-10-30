"""Bounded binary NetFlow-v5 teaching collector and isolated fixture probes.

Wire fields follow Cisco's NetFlow Export Datagram Format, tables B-3/B-4:
https://www.cisco.com/c/en/us/td/docs/net_mgmt/netflow_collection_engine/3-6/user/guide/format.html
This is not Secure Network Analytics/Stealthwatch or an authenticated feed.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import struct
import threading
import time
from pathlib import Path

HEADER = struct.Struct("!HHIIIIBBH")
RECORD = struct.Struct("!IIIHHIIIIHHBBBBHHBBH")


def address(value):
    ip = ipaddress.IPv4Address(value)
    if not (ip in ipaddress.IPv4Network("198.18.0.0/15") or ip.is_loopback):
        raise ValueError("Only isolated benchmark/loopback IPv4 addresses are accepted")
    return str(ip)


def parse_v5(data):
    if len(data) < HEADER.size:
        raise ValueError("Truncated NetFlow header")
    header = HEADER.unpack_from(data)
    if header[0] != 5 or not 1 <= header[1] <= 30 or header[4] >= 1_000_000_000:
        raise ValueError("Invalid NetFlow-v5 header")
    if len(data) != HEADER.size + header[1] * RECORD.size:
        raise ValueError("NetFlow count/length mismatch")
    result = []
    for index in range(header[1]):
        values = RECORD.unpack_from(data, HEADER.size + index * RECORD.size)
        result.append(
            {
                "source": str(ipaddress.IPv4Address(values[0])),
                "destination": str(ipaddress.IPv4Address(values[1])),
                "packets": values[5],
                "bytes": values[6],
                "source_port": values[9],
                "destination_port": values[10],
                "protocol": values[13],
                "tos": values[14],
                "sequence": header[5],
            }
        )
    return result


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".next")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    for attempt in range(20):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.01)


def snapshot(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"datagrams": 0, "rejected": 0, "records": []}


class Collector:
    def __init__(self, bind, port, exporter, state):
        self.exporter = address(exporter)
        self.path = state
        self.stop = threading.Event()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((address(bind), port))
        self.socket.settimeout(0.1)
        self.state = {"datagrams": 0, "rejected": 0, "records": []}
        save(self.path, self.state)

    def run(self):
        while not self.stop.is_set():
            try:
                data, peer = self.socket.recvfrom(4096)
            except TimeoutError:
                continue
            try:
                if peer[0] != self.exporter:
                    raise ValueError("Unexpected exporter source")
                records = parse_v5(data)
                self.state["records"] = [*self.state["records"], *records][-256:]
                self.state["datagrams"] += 1
            except ValueError:
                self.state["rejected"] += 1
            save(self.path, self.state)

    def close(self):
        self.stop.set()


def matching(state, port):
    return [
        r
        for r in state["records"]
        if r["source"] == "198.18.10.10"
        and r["destination"] == "198.18.20.20"
        and r["protocol"] == 6
        and r["destination_port"] == port
        and r["packets"] > 0
        and r["bytes"] > 0
    ]


def proof(path, port):
    state = snapshot(path)
    records = matching(state, port)
    return {
        "observed": bool(records),
        "matching_records": len(records),
        "datagrams": state["datagrams"],
        "port": port,
    }


def quiet(path, port, seconds=40):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if matching(snapshot(path), port):
            return {"quiet": False, "port": port}
        time.sleep(min(0.2, max(0, end - time.monotonic())))
    return {"quiet": True, "port": port, "seconds": seconds}


def analyze(path, suppress_scan=False):
    records = snapshot(path)["records"]
    ports = sorted(
        {
            r["destination_port"]
            for r in records
            if r["source"] == "198.18.10.10"
            and r["destination"] == "198.18.20.20"
            and r["protocol"] == 6
            and r["packets"] > 0
            and r["bytes"] > 0
        }
    )
    evaluated = [p for p in ports if not (suppress_scan and 10000 <= p <= 10006)]
    return {
        "flagged": len(evaluated) >= 6,
        "distinct_ports": len(ports),
        "evaluated_ports": len(evaluated),
        "suppression": suppress_scan,
    }


def scan():
    for port in range(10000, 10007):
        try:
            with socket.create_connection(("198.18.20.20", port), timeout=0.5):
                pass
        except OSError:
            pass
    return {"fixture_tcp_attempts": 7, "destination": "198.18.20.20"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("receive", "proof", "quiet", "scan", "analyze"))
    parser.add_argument("service_port", type=int, nargs="?", default=8080)
    parser.add_argument("--state", type=Path, default=Path("/lab/netflow.json"))
    parser.add_argument("--bind", type=address, default="198.18.20.20")
    parser.add_argument("--exporter", type=address, default="198.18.20.1")
    parser.add_argument("--port", type=int, default=2055)
    parser.add_argument("--suppress-scan", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or not 1 <= args.service_port <= 65535:
        parser.error("Invalid fixture port")
    if args.action == "receive":
        collector = Collector(args.bind, args.port, args.exporter, args.state)
        try:
            collector.run()
        finally:
            collector.socket.close()
        return
    if args.action == "proof":
        result = proof(args.state, args.service_port)
    elif args.action == "quiet":
        result = quiet(args.state, args.service_port)
    elif args.action == "analyze":
        result = analyze(args.state, args.suppress_scan)
    else:
        result = scan()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
