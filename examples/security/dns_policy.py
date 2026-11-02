"""Closed authoritative DNS policy fixture; no recursion or external queries."""

import argparse
import ipaddress
import json
import os
import re
import socketserver
import struct
import subprocess
import threading
from pathlib import Path

ROOT = Path("/lab")
HOST = "198.18.0.1"
GOOD = "allowed.lab.example"
BAD = "blocked.lab.example"
MODES = ("enforce", "bypass", "unavailable")


def question(packet):
    if not 17 <= len(packet) <= 512:
        raise ValueError("Bounded DNS message required")
    ident, flags, qd, an, ns, ar = struct.unpack("!6H", packet[:12])
    if flags & ~0x0100 or (qd, an, ns, ar) != (1, 0, 0, 0):
        raise ValueError("Only one standard uncompressed question without EDNS")
    pos, labels = 12, []
    while True:
        if pos >= len(packet):
            raise ValueError("Truncated question")
        length = packet[pos]
        pos += 1
        if length == 0:
            break
        if length > 63 or pos + length > len(packet):
            raise ValueError("Compressed or truncated label")
        label = packet[pos : pos + length].decode("ascii")
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label):
            raise ValueError("Label outside fixed hostname profile")
        labels.append(label)
        pos += length
    if not labels or pos - 12 > 255 or pos + 4 != len(packet):
        raise ValueError("Invalid name size or trailing data")
    qtype, qclass = struct.unpack("!HH", packet[pos:])
    return ident, flags, ".".join(labels).lower(), qtype, qclass


def answer(packet, mode):
    if mode not in MODES:
        raise ValueError("Unknown local policy")
    try:
        ident, flags, name, qtype, qclass = question(packet)
    except (ValueError, UnicodeError, struct.error):
        ident = struct.unpack("!H", packet[:2])[0] if len(packet) >= 2 else 0
        return struct.pack("!6H", ident, 0x8001, 0, 0, 0, 0)
    response_flags = 0x8000 | (flags & 0x0100)
    records = b""
    if qtype != 1 or qclass != 1:
        code = 4
    elif name not in (GOOD, BAD):
        code = 5
    elif mode == "unavailable":
        code = 2
    elif name == BAD and mode == "enforce":
        code = 3
    else:
        code = 0
        # Exact question-name pointer, IN A, zero TTL, fixed benchmark answer.
        records = (
            b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 0, 4) + ipaddress.IPv4Address(HOST).packed
        )
    # Intentionally not AA: this policy block is not an authoritative zone denial.
    return (
        struct.pack("!6H", ident, response_flags | code, 1, bool(records), 0, 0)
        + packet[12:]
        + records
    )


def policy():
    mode = (ROOT / "dns-mode").read_text().strip()
    if mode not in MODES:
        raise ValueError("Unknown fixture state")
    return mode


class UDP(socketserver.BaseRequestHandler):
    def handle(self):
        packet, sock = self.request
        sock.sendto(answer(packet, policy()), self.client_address)


def read_exact(stream, count):
    data = b""
    while len(data) < count:
        part = stream.recv(count - len(data))
        if not part:
            raise ValueError("Incomplete DNS TCP frame")
        data += part
    return data


class TCP(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(3)
        try:
            length = struct.unpack("!H", read_exact(self.request, 2))[0]
            if not 17 <= length <= 512:
                return
            response = answer(read_exact(self.request, length), policy())
            self.request.sendall(struct.pack("!H", len(response)) + response)
        except (ValueError, TimeoutError, ConnectionError):
            return


def serve():
    with (
        socketserver.ThreadingUDPServer((HOST, 53), UDP) as udp,
        socketserver.ThreadingTCPServer((HOST, 53), TCP) as tcp,
    ):
        udp.daemon_threads = tcp.daemon_threads = True
        threading.Thread(target=udp.serve_forever, daemon=True).start()
        tcp.serve_forever()


def dig(name, tcp=False, qtype="A"):
    assert name in (GOOD, BAD, "outside.lab.example") and qtype in ("A", "AAAA")
    result = subprocess.run(
        [
            "dig",
            "@" + HOST,
            name,
            qtype,
            "+noedns",
            "+norecurse",
            "+noadflag",
            "+nocdflag",
            "+time=2",
            "+tries=1",
            "+tcp" if tcp else "+notcp",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    text = result.stdout
    status = re.findall(r"->>HEADER<<-.*status: ([A-Z]+),", text)
    assert len(status) == 1
    count = re.findall(r"QUERY: 1, ANSWER: ([0-9]+), AUTHORITY: 0, ADDITIONAL: 0", text)
    assert len(count) == 1
    records = re.findall(r"(?m)^([a-z.]+)\s+(\d+)\s+IN\s+A\s+([0-9.]+)\s*$", text)
    assert int(count[0]) == len(records)
    assert ";; flags: qr;" in text, "No recursion or authority must be advertised"
    return status[0], records


def probe(phase):
    assert phase in ("enforce", "bypass", "unavailable", "recovered")
    mode = "enforce" if phase == "recovered" else phase
    expected_good = "SERVFAIL" if mode == "unavailable" else "NOERROR"
    expected_bad = {
        "enforce": "NXDOMAIN",
        "bypass": "NOERROR",
        "unavailable": "SERVFAIL",
    }[mode]
    observations = []
    for tcp in (False, True):
        for name, expected in (
            (GOOD, expected_good),
            (BAD, expected_bad),
            ("outside.lab.example", "REFUSED"),
        ):
            status, records = dig(name, tcp)
            assert status == expected
            assert records == ([(name + ".", "0", HOST)] if expected == "NOERROR" else [])
            observations.append(
                {
                    "name": name,
                    "transport": "tcp" if tcp else "udp",
                    "rcode": status,
                    "answers": len(records),
                }
            )
        status, records = dig(GOOD, tcp, "AAAA")
        assert status == "NOTIMP" and records == []
    return {
        "status": "passed",
        "phase": phase,
        "independent_client": "dig",
        "observations": observations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "serve",
            "enforce",
            "bypass",
            "unavailable",
            "probe-enforce",
            "probe-bypass",
            "probe-unavailable",
            "probe-recovered",
        ),
    )
    args = parser.parse_args()
    assert (ROOT / "CML-DNS-POLICY").read_text().strip() == "CML-DNS-POLICY-V1"
    if args.action == "serve":
        assert os.geteuid() == 0
        serve()
        return
    if args.action in MODES:
        assert os.geteuid() == 0
        p = ROOT / "dns-mode"
        assert not p.is_symlink()
        temp = p.with_suffix(".next")
        with temp.open("x", encoding="ascii") as stream:
            stream.write(args.action + "\n")
        temp.chmod(0o600)
        temp.replace(p)
        value = {"status": "passed", "policy": args.action}
    else:
        value = probe(args.action.removeprefix("probe-"))
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
