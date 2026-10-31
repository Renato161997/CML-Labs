"""Kernel MACsec classroom fixture: wire evidence, wrong-key drops and PN continuity."""

import argparse
import json
import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-MACSEC-CLASSROOM-V1"
DATA = "eth1"
DEVICE = "macsec0"
# Public teaching vectors. No confidentiality or production key-management claim.
GOOD = "00112233445566778899aabbccddeeff"
EXPECTED = "102132435465768798a9bacbdcedfe0f"
WRONG = "ffeeddccbbaa99887766554433221100"
IDS = ["01000000000000000000000000000000", "02000000000000000000000000000000"]
MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}")


def run(argv, check=True):
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=20,
        check=check,
        env={**os.environ, "LC_ALL": "C"},
        stdin=subprocess.DEVNULL,
    )


def role():
    value = (ROOT / "macsec-role").read_text().strip()
    if value not in ("LEFT", "RIGHT"):
        raise ValueError("Unknown MACsec endpoint")
    return value


def addresses(kind):
    number = 1 if kind == "LEFT" else 2
    return (
        "198.18.0." + str(number),
        "198.19.0." + str(number),
        "198.18.0." + str(3 - number),
        "198.19.0." + str(3 - number),
    )


def frame(data):
    if len(data) < 14 or data[12:14] != b"\x88\xe5":
        return None
    if len(data) < 46:
        raise ValueError("Truncated MACsec frame")
    tci, length = data[14], data[15]
    if tci & 0xD0 or tci & 0x2C != 0x2C:
        raise ValueError("The exercise requires SCI-present encrypted version-zero frames")
    sci, packet = int.from_bytes(data[20:28], "big"), int.from_bytes(data[16:20], "big")
    if not packet or sci >> 16 != int.from_bytes(data[6:12], "big") or sci & 65535 != 1:
        raise ValueError("Unexpected SCI, source identity or packet number")
    secure_length = len(data) - 44
    if not ((length == 0 and secure_length >= 48) or (0 < length < 48 and length == secure_length)):
        raise ValueError("Inconsistent protected-data length")
    return {"sci": sci, "an": tci & 3, "pn": packet, "length": len(data)}


def status():
    values = json.loads(run(["ip", "-s", "-j", "macsec", "show"]).stdout)
    selected = [value for value in values if value.get("ifname") == DEVICE]
    assert len(selected) == 1
    return selected[0]


def association(values, an):
    selected = [item for item in values if item.get("an") == an]
    assert len(selected) == 1 and selected[0]["active"] is True
    value = selected[0]
    assert value["key"] == IDS[an] and type(value["pn"]) is int and value["pn"] > 0
    return value


def read_state():
    value = json.loads((ROOT / "macsec-state.json").read_text())
    assert set(value) == {"own_mac", "peer_mac", "own_sci", "peer_sci", "sa0_floor"}
    assert MAC.fullmatch(value["own_mac"]) and MAC.fullmatch(value["peer_mac"])
    for name in ("own", "peer"):
        assert value[name + "_sci"] == (int(value[name + "_mac"].replace(":", ""), 16) << 16) | 1
    assert type(value["sa0_floor"]) is int and value["sa0_floor"] > 0
    return value


def save_state(state):
    temporary = ROOT / "macsec-state.tmp"
    temporary.write_text(json.dumps(state, sort_keys=True))
    temporary.replace(ROOT / "macsec-state.json")


def worker_owned(pid):
    if type(pid) is not int or pid <= 1:
        raise ValueError("Unsafe provisioning PID")
    try:
        args = (Path("/proc") / str(pid) / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    except FileNotFoundError:
        return False
    return args == [
        os.fsencode(sys.executable),
        os.fsencode(Path(__file__).resolve()),
        b"configure",
    ]


def wait_state():
    deadline = time.monotonic() + 65
    while not (ROOT / "macsec-state.json").exists():
        path = ROOT / "macsec-configure.pid"
        if path.exists() and not worker_owned(int(path.read_text())):
            raise RuntimeError(
                "Provisioning did not finish; inspect the owned guest log and wipe this copy before retrying"
            )
        if time.monotonic() >= deadline:
            raise TimeoutError("The owned MACsec provisioner did not finish")
        time.sleep(0.5)
    return read_state()


def start():
    if (ROOT / "macsec-state.json").exists():
        return {"started": True, "already_configured": True}
    path = ROOT / "macsec-configure.pid"
    if path.exists():
        assert worker_owned(int(path.read_text())), (
            "Refuse to restart a failed or foreign provisioner over existing security associations"
        )
        return {"started": True}
    with (ROOT / "macsec-configure.log").open("ab") as output:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "configure"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            start_new_session=True,
        )
    path.write_text(str(child.pid))
    return {"started": True}


def verify(value, state, encoding):
    assert type(encoding) is int and encoding in (0, 1)
    assert value["protect"] is True and value["encrypt"] is True and value["send_sci"] is True
    assert value["validate"] == "strict" and value["replay"] is True and value["window"] == 0
    assert (
        value["cipher_suite"] == "GCM-AES-128"
        and value["icv_length"] == 16
        and value["offload"] == "off"
    )
    assert int(value["sci"], 16) == state["own_sci"] and value["encoding_sa"] == encoding
    sa0 = association(value["sa_list"], 0)
    assert sa0["pn"] >= state["sa0_floor"], "A transmit packet number must never be reset"
    assert len(value["rx_sc"]) == 1
    rx = value["rx_sc"][0]
    assert rx["active"] is True and int(rx["sci"], 16) == state["peer_sci"]
    association(rx["sa_list"], 0)
    return rx


def packet_counts(output):
    found = re.search(r"(\d+) (?:packets )?transmitted, (\d+) received", output)
    assert found, "Missing actual ping packet counts"
    return int(found[1]), int(found[2])


def ping(target, device):
    return run(["ping", "-I", device, "-c", "3", "-W", "2", target], False)


def configure(kind):
    if (ROOT / "macsec-state.json").exists():
        state = read_state()
        verify(status(), state, 0 if kind == "RIGHT" else status()["encoding_sa"])
        return {"configured": True, "reused_without_sa_reset": True}
    assert run(["ip", "link", "show", "dev", DEVICE], False).returncode != 0, (
        "Refuse an unowned existing SecY"
    )
    control, overlay, _, target = addresses(kind)
    raw = bytearray(secrets.token_bytes(6))
    raw[0] = (raw[0] | 2) & 254
    own = ":".join(f"{byte:02x}" for byte in raw)
    for command in [
        ["ip", "link", "set", DATA, "down"],
        ["ip", "link", "set", DATA, "address", own],
        ["ip", "address", "replace", control + "/30", "dev", DATA],
        ["ip", "link", "set", DATA, "up"],
        [
            "ip",
            "link",
            "add",
            "link",
            DATA,
            "name",
            DEVICE,
            "type",
            "macsec",
            "port",
            "1",
            "encrypt",
            "on",
            "protect",
            "on",
            "send_sci",
            "on",
            "validate",
            "strict",
            "replay",
            "on",
            "window",
            "0",
        ],
        ["ip", "macsec", "add", DEVICE, "tx", "sa", "0", "pn", "1", "on", "key", IDS[0], GOOD],
    ]:
        run(command)
    if kind == "LEFT":
        run(["ip", "macsec", "add", DEVICE, "tx", "sa", "1", "pn", "1", "on", "key", IDS[1], WRONG])
    own_sci = (int(own.replace(":", ""), 16) << 16) | 1
    capture = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    capture.bind((DATA, 0))
    capture.settimeout(0.2)
    try:
        run(["ip", "address", "add", overlay + "/30", "dev", DEVICE])
        run(["ip", "link", "set", DEVICE, "up"])
        peer_sci = None
        deadline = time.monotonic() + 50
        while peer_sci is None and time.monotonic() < deadline:
            # Both point-to-point peers advertise their fresh SCI in actual protected ARP.
            run(["ping", "-I", DEVICE, "-c", "1", "-W", "1", target], False)
            until = time.monotonic() + 0.7
            while time.monotonic() < until:
                try:
                    data = capture.recv(4096)
                except TimeoutError:
                    continue
                item = frame(data)
                if item and item["sci"] != own_sci and item["an"] == 0:
                    peer_sci = item["sci"]
                    break
        assert peer_sci is not None, "The other owned point-to-point peer did not advertise an SCI"
    finally:
        capture.close()
    peer = ":".join(f"{byte:02x}" for byte in (peer_sci >> 16).to_bytes(6, "big"))
    run(["ip", "macsec", "add", DEVICE, "rx", "sci", f"{peer_sci:016x}", "on"])
    run(
        [
            "ip",
            "macsec",
            "add",
            DEVICE,
            "rx",
            "sci",
            f"{peer_sci:016x}",
            "sa",
            "0",
            "pn",
            "1",
            "on",
            "key",
            IDS[0],
            GOOD,
        ]
    )
    if kind == "RIGHT":
        run(
            [
                "ip",
                "macsec",
                "add",
                DEVICE,
                "rx",
                "sci",
                f"{peer_sci:016x}",
                "sa",
                "1",
                "pn",
                "1",
                "on",
                "key",
                IDS[1],
                EXPECTED,
            ]
        )
    state = {
        "own_mac": own,
        "peer_mac": peer,
        "own_sci": own_sci,
        "peer_sci": peer_sci,
        "sa0_floor": 1,
    }
    verify(status(), state, 0)
    save_state(state)
    return {"configured": True, "fresh_sci": True}


def interfaces(kind, state):
    control, overlay, _, _ = addresses(kind)
    for device, address in ((DATA, control), (DEVICE, overlay)):
        rows = json.loads(run(["ip", "-j", "address", "show", "dev", device]).stdout)
        assert len(rows) == 1 and "UP" in rows[0]["flags"]
        assert {
            (item["local"], item["prefixlen"])
            for item in rows[0]["addr_info"]
            if item["family"] == "inet"
        } == {(address, 30)}
        assert rows[0]["address"] == state["own_mac"]


def check(kind, encoding):
    state = wait_state()
    value = status()
    verify(value, state, encoding)
    interfaces(kind, state)
    control = ping(addresses(kind)[2], DATA)
    assert control.returncode == 0 and packet_counts(control.stdout) == (3, 3)
    state["sa0_floor"] = association(value["sa_list"], 0)["pn"]
    save_state(state)
    return {
        "status": "passed",
        "role": kind,
        "encoding_sa": encoding,
        "sa0_next_pn": state["sa0_floor"],
        "underlay_received": 3,
        "kernel": platform.release(),
    }


def select(kind, encoding):
    assert kind == "LEFT" and type(encoding) is int and encoding in (0, 1)
    state = wait_state()
    before = status()
    verify(before, state, before["encoding_sa"])
    state["sa0_floor"] = association(before["sa_list"], 0)["pn"]
    run(["ip", "link", "set", "dev", DEVICE, "type", "macsec", "encodingsa", str(encoding)])
    verify(status(), state, encoding)
    save_state(state)
    return {"selected": True, "encoding_sa": encoding, "sa0_not_reset": True}


def measure(kind, expected):
    assert kind == "RIGHT"
    state = wait_state()
    interfaces(kind, state)
    before = status()
    rx_before = verify(before, state, 0)
    frames = []
    invalid = []
    stop = threading.Event()
    capture = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    capture.bind((DATA, 0))
    capture.settimeout(0.2)

    def observe():
        while not stop.is_set():
            try:
                data = capture.recv(4096)
            except TimeoutError:
                continue
            if data[6:12].hex() != state["peer_mac"].replace(":", ""):
                continue
            try:
                item = frame(data)
            except ValueError:
                invalid.append(True)
                continue
            if item:
                if len(frames) >= 256:
                    invalid.append(True)
                else:
                    frames.append(item)

    worker = threading.Thread(target=observe)
    worker.start()
    try:
        packets = ping(addresses(kind)[3], DEVICE)
        time.sleep(0.4)
    finally:
        stop.set()
        worker.join(2)
        capture.close()
    assert not worker.is_alive() and not invalid
    after = status()
    rx_after = verify(after, state, 0)
    received = 3 if expected == "up" else 0
    assert packet_counts(packets.stdout) == (3, received) and (packets.returncode == 0) == (
        received == 3
    )
    an = 0 if expected == "up" else 1
    matching = [item for item in frames if item["sci"] == state["peer_sci"] and item["an"] == an]
    assert len(matching) >= 3, "Fresh expected-peer encrypted wire frames were not observed"
    assert after["OutPktsEncrypted"] - before["OutPktsEncrypted"] >= 3
    metric = "InPktsOK" if expected == "up" else "InPktsNotValid"
    a = association(rx_before["sa_list"], an)
    b = association(rx_after["sa_list"], an)
    delta = b[metric] - a[metric]
    assert delta >= 3, "Expected authenticated delivery or wrong-key drops were not measured"
    control = ping(addresses(kind)[2], DATA)
    assert control.returncode == 0 and packet_counts(control.stdout) == (3, 3)
    return {
        "status": "passed",
        "received": received,
        "wire_an": an,
        "encrypted_frames": len(matching),
        "counter": metric,
        "counter_delta": delta,
        "underlay_received": 3,
        "kernel": platform.release(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "configure", "check", "select", "measure"))
    parser.add_argument("--encoding", type=int, choices=(0, 1), default=0)
    parser.add_argument("--expect", choices=("up", "down"), default="up")
    args = parser.parse_args()
    if os.geteuid() != 0 or (ROOT / "CML-MACSEC-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only marked, owned disposable MACsec guests are accepted")
    kind = role()
    result = (
        start()
        if args.action == "start"
        else configure(kind)
        if args.action == "configure"
        else check(kind, args.encoding)
        if args.action == "check"
        else select(kind, args.encoding)
        if args.action == "select"
        else measure(kind, args.expect)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
