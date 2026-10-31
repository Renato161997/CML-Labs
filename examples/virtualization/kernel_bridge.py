"""Actual Linux bridge VLAN isolation with an independent tagged control path."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-VIRTUAL-BRIDGE-V1"
ROLES = {"SW", "LEFT", "RIGHT"}


def run(args, check=True):
    return subprocess.run(
        args,
        check=check,
        text=True,
        capture_output=True,
        timeout=15,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "LC_ALL": "C"},
    )


def read(args):
    return json.loads(run(args).stdout)


def role():
    value = (ROOT / "bridge-role").read_text().strip()
    assert value in ROLES
    return value


def configure(label):
    if label == "SW":
        run(["ip", "link", "add", "br0", "type", "bridge", "vlan_filtering", "1"])
        run(["ip", "link", "set", "br0", "up"])
        for port in ("eth1", "eth2"):
            run(["ip", "link", "set", port, "up"])
            run(["ip", "link", "set", port, "master", "br0"])
            run(["bridge", "vlan", "del", "dev", port, "vid", "1"])
            run(["bridge", "vlan", "add", "dev", port, "vid", "10", "pvid", "untagged"])
            run(["bridge", "vlan", "add", "dev", port, "vid", "99"])
        run(["bridge", "vlan", "add", "dev", "br0", "vid", "99", "self"])
        run(["ip", "link", "add", "link", "br0", "name", "br0.99", "type", "vlan", "id", "99"])
        run(["ip", "address", "add", "198.18.1.1/29", "dev", "br0.99"])
        run(["ip", "link", "set", "br0.99", "up"])
    else:
        suffix = 1 if label == "LEFT" else 2
        run(["ip", "link", "set", "eth1", "up"])
        run(["ip", "address", "add", f"198.18.0.{suffix}/30", "dev", "eth1"])
        run(["ip", "link", "add", "link", "eth1", "name", "eth1.99", "type", "vlan", "id", "99"])
        run(["ip", "address", "add", f"198.18.1.{suffix + 1}/29", "dev", "eth1.99"])
        run(["ip", "link", "set", "eth1.99", "up"])
    return {"status": "passed", "configured": label}


def port_vlan(rows, port, data_vlan):
    candidates = [row for row in rows if row.get("ifname") == port]
    assert len(candidates) == 1, "Expected one actual bridge port record"
    entries = candidates[0]["vlans"]
    assert len(entries) == 2 and {item["vlan"] for item in entries} == {data_vlan, 99}
    for item in entries:
        flags = {flag.lower().replace(" ", "-") for flag in item.get("flags", [])}
        assert flags == ({"pvid", "egress-untagged"} if item["vlan"] == data_vlan else set())


def switch_state(split):
    assert role() == "SW"
    detail = read(["ip", "-d", "-j", "link", "show", "br0"])[0]
    assert detail["linkinfo"]["info_kind"] == "bridge"
    assert detail["linkinfo"]["info_data"]["vlan_filtering"] == 1
    rows = read(["bridge", "-j", "vlan", "show"])
    port_vlan(rows, "eth1", 10)
    port_vlan(rows, "eth2", 20 if split else 10)
    links = read(["bridge", "-j", "link", "show"])
    for port in ("eth1", "eth2"):
        entry = next(row for row in links if row["ifname"] == port)
        assert entry["state"] == "forwarding" and entry.get("master") == "br0"
    return {
        "status": "passed",
        "vlan_split": split,
        "tagged_control_vlan": 99,
        "kernel_release": os.uname().release,
    }


def state():
    assert role() == "SW"
    rows = read(["bridge", "-j", "vlan", "show"])
    entry = next(row for row in rows if row["ifname"] == "eth2")
    candidates = {item["vlan"] for item in entry["vlans"]}.intersection({10, 20})
    assert len(candidates) == 1, "Refuse an unknown or leaking data-VLAN state"
    return switch_state(20 in candidates)


def change(split):
    assert role() == "SW" and type(split) is bool
    actual = state()["vlan_split"]
    if actual != split:
        old, new = (10, 20) if split else (20, 10)
        run(["bridge", "vlan", "del", "dev", "eth2", "vid", str(old)])
        run(["bridge", "vlan", "add", "dev", "eth2", "vid", str(new), "pvid", "untagged"])
    return switch_state(split)


def ping(interface, address, received):
    run(["ping", "-I", interface, "-c", "1", "-W", "1", address], False)
    result = run(["ping", "-I", interface, "-c", "3", "-i", "0.2", "-W", "1", address], False)
    counts = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received", result.stdout)
    assert counts and (int(counts[1]), int(counts[2])) == (3, received), (
        "Actual bound IPv4 probes disagree"
    )
    assert result.returncode == (0 if received else 1)


def probe(split):
    label = role()
    assert label in ("LEFT", "RIGHT")
    own = 1 if label == "LEFT" else 2
    for interface, expected in [("eth1", f"198.18.0.{own}"), ("eth1.99", f"198.18.1.{own + 1}")]:
        addresses = read(["ip", "-j", "address", "show", "dev", interface])[0]["addr_info"]
        assert [entry["local"] for entry in addresses if entry["family"] == "inet"] == [expected]
    ping("eth1.99", "198.18.1.1", 3)
    ping("eth1", f"198.18.0.{3 - own}", 0 if split else 3)
    return {"status": "passed", "control_replies": 3, "data_replies": 0 if split else 3}


def dynamic(entry, mac, port):
    states = entry.get("state", [])
    states = [states] if isinstance(states, str) else states
    return (
        entry.get("mac", "").lower() == mac.lower()
        and entry.get("ifname") == port
        and entry.get("vlan") == 10
        and entry.get("master") == "br0"
        and not {"permanent", "static", "noarp"}.intersection(states)
        and not {"self", "extern_learn", "sticky"}.intersection(entry.get("flags", []))
    )


def learned():
    switch_state(False)
    neighbors = read(["ip", "-j", "neigh", "show", "dev", "br0.99"])
    macs = {entry["dst"]: entry["lladdr"] for entry in neighbors if "lladdr" in entry}
    entries = read(["bridge", "-j", "fdb", "show", "br", "br0"])
    for address, port in [("198.18.1.2", "eth1"), ("198.18.1.3", "eth2")]:
        assert address in macs and any(dynamic(entry, macs[address], port) for entry in entries)
    return {"status": "passed", "dynamic_data_mac_entries": 2, "data_vlan": 10}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("configure", "check", "split", "restore", "good", "isolated", "fdb")
    )
    action = parser.parse_args().action
    if os.geteuid() != 0 or (ROOT / "CML-BRIDGE-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the own disposable bridge fixture is accepted")
    if action == "configure":
        result = configure(role())
    elif action == "check":
        result = state()
    elif action in ("split", "restore"):
        result = change(action == "split")
    elif action == "fdb":
        result = learned()
    else:
        result = probe(action == "isolated")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
