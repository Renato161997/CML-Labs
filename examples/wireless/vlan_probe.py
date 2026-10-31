"""Observe real simulated Wi-Fi bridging and the Linux 802.1Q uplink."""

import argparse
import json
import os
import time

import radio_probe as radio

CLIENT = "198.18.10.2"
TARGET = "198.18.10.1"
CONTROL = "198.18.0.2"


def interface(name):
    result = radio.run_command(["ip", "-j", "-d", "link", "show", "dev", name], check=False)
    if result.returncode:
        return None
    rows = json.loads(result.stdout)
    assert len(rows) == 1 and rows[0]["ifname"] == name
    return rows[0]


def ensure_link(name, kind, arguments):
    item = interface(name)
    if item is None:
        radio.run_command(["ip", "link", "add", *arguments, "name", name, "type", kind])
        item = interface(name)
    assert item["linkinfo"]["info_kind"] == kind
    return item


def mapping(links, vlan):
    if vlan not in (10, 20) or set(links) != {"br0", "v10", "v20", "wlan0"}:
        raise ValueError("Only the classroom radio bridge and its two tagged uplinks are accepted")
    assert links["br0"]["linkinfo"]["info_kind"] == "bridge"
    assert "UP" in links["br0"]["flags"] and links["wlan0"].get("master") == "br0"
    for tag in (10, 20):
        item = links["v" + str(tag)]
        assert item["linkinfo"]["info_kind"] == "vlan"
        assert item["linkinfo"]["info_data"]["id"] == tag
        assert item.get("link") == "ens2" and "UP" in item["flags"]
        assert item.get("master") == ("br0" if tag == vlan else None)
    return {"radio_bridge": "br0", "uplink_vlan": vlan}


def remap(vlan):
    if vlan not in (10, 20):
        raise ValueError("Unexpected VLAN")
    for tag in (10, 20):
        name = "v" + str(tag)
        item = interface(name)
        assert item["linkinfo"]["info_kind"] == "vlan"
        assert item["linkinfo"]["info_data"]["id"] == tag
        assert item.get("link") == "ens2"
        radio.run_command(["ip", "link", "set", "dev", name, "nomaster"])
    radio.run_command(["ip", "link", "set", "dev", "v" + str(vlan), "master", "br0"])
    return {
        "configured": True,
        **mapping({name: interface(name) for name in ("br0", "v10", "v20", "wlan0")}, vlan),
    }


def configure(value):
    radio.configure(value, "none")
    old = radio.TARGET if value["role"] == "ap" else radio.CLIENT
    radio.run_command(["ip", "address", "del", old + "/24", "dev", "wlan0"])
    if value["role"] == "client":
        radio.run_command(["ip", "address", "replace", CLIENT + "/24", "dev", "wlan0"])
        return {"configured": True, "role": "client"}
    ensure_link("br0", "bridge", [])
    for tag in (10, 20):
        name = "v" + str(tag)
        item = interface(name)
        if item is None:
            radio.run_command(
                ["ip", "link", "add", "link", "ens2", "name", name, "type", "vlan", "id", str(tag)]
            )
        radio.run_command(["ip", "link", "set", "dev", name, "up"])
    radio.run_command(["ip", "link", "set", "dev", "wlan0", "master", "br0"])
    radio.run_command(["ip", "link", "set", "dev", "br0", "up"])
    radio.run_command(["ip", "link", "set", "dev", "ens2", "up"])
    radio.run_command(["ip", "address", "replace", "198.18.0.1/30", "dev", "ens2"])
    return {"role": "ap", **remap(10)}


def ping(destination, device):
    result = radio.run_command(
        ["ping", "-I", device, "-c", "3", "-W", "2", destination], check=False
    )
    sent, received = radio.packet_counts(result.stdout)
    assert sent == 3
    assert (result.returncode == 0) == (received == 3)
    return received


def client_address(rows):
    assert len(rows) == 1 and rows[0]["ifname"] == "wlan0" and "UP" in rows[0]["flags"]
    actual = {
        (item["local"], item["prefixlen"])
        for item in rows[0]["addr_info"]
        if item["family"] == "inet"
    }
    assert actual == {(CLIENT, 24)}, "The fault must preserve the actual WLAN client address"


def associated(value):
    status, link = radio.snapshot()
    assert all(radio.association(status, link, value).values()), (
        "Radio association must remain healthy even when VLAN forwarding fails"
    )


def check(value, expected, vlan):
    if value["role"] == "ap":
        status = radio.parse_status(
            radio.run_command(["hostapd_cli", "-i", "wlan0", "status"]).stdout
        )
        assert status.get("state") == "ENABLED" and status.get("ssid[0]") == value["ssid"]
        actual = mapping({name: interface(name) for name in ("br0", "v10", "v20", "wlan0")}, vlan)
        assert ping(CONTROL, "ens2") == 3, "The independent untagged uplink must remain healthy"
        return {"status": "passed", "role": "ap", "control_received": 3, **actual}
    rows = json.loads(radio.run_command(["ip", "-j", "address", "show", "dev", "wlan0"]).stdout)
    client_address(rows)
    if expected == "down":
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            associated(value)
            time.sleep(2)
        radio.run_command(["ip", "neigh", "flush", "dev", "wlan0"])
        assert ping(TARGET, "wlan0") == 0
        associated(value)
        return {"status": "passed", "role": "client", "associated": True, "received": 0}
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            associated(value)
            radio.run_command(["ip", "neigh", "flush", "dev", "wlan0"])
            if ping(TARGET, "wlan0") == 3:
                return {"status": "passed", "role": "client", "associated": True, "received": 3}
        except AssertionError:
            pass
        time.sleep(2)
    raise TimeoutError("The actual WLAN-to-VLAN packet path did not recover")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("configure", "map", "check"))
    parser.add_argument("--vlan", type=int, choices=(10, 20), default=10)
    parser.add_argument("--expect", choices=("up", "down"), default="up")
    args = parser.parse_args()
    if (
        os.geteuid() != 0
        or (radio.ROOT / "CML-WIRELESS-FIXTURE").read_text().strip() != radio.MARKER
    ):
        raise PermissionError("Only a marked, owned disposable radio guest is accepted")
    value = radio.settings(json.loads((radio.ROOT / "wireless.json").read_text()))
    if args.action == "map" and value["role"] != "ap":
        raise ValueError("Only the AP may remap the classroom uplink")
    result = (
        configure(value)
        if args.action == "configure"
        else remap(args.vlan)
        if args.action == "map"
        else check(value, args.expect, args.vlan)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
