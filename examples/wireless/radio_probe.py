"""Real hostapd/wpa_supplicant checks, confined to disposable CML radio guests."""

import argparse
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path("/lab")
PROC = Path("/proc")
MARKER = "CML-WIRELESS-FIXTURE-V1"
TARGET = "198.18.50.1"
CLIENT = "198.18.50.2"
KEY = "Cml-Wifi-Only-983"  # Public teaching fixture, never a production secret.
MAC = re.compile(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", re.IGNORECASE)


def settings(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"role", "auth", "ssid"}
        or value["role"] not in ("ap", "client")
        or value["auth"] not in ("open", "wpa2")
        or not isinstance(value["ssid"], str)
        or not re.fullmatch(r"CML-[A-Z0-9-]{1,16}", value["ssid"])
    ):
        raise ValueError("Only the declared disposable radio settings are accepted")
    return value


def configuration(value, fault="none"):
    value = settings(value)
    role, auth, ssid = (value[key] for key in ("role", "auth", "ssid"))
    if fault not in ("none", "ssid", "key") or (role == "ap" and fault != "none"):
        raise ValueError("Unsupported radio fault")
    if fault == "key" and auth != "wpa2":
        raise ValueError("An open WLAN has no PSK to invalidate")
    if role == "ap":
        base = (
            "interface=wlan0\ndriver=nl80211\nctrl_interface=/run/hostapd\n"
            f"ssid={ssid}\nchannel=6\nauth_algs=1\n"
        )
        return base + (
            "wpa=0\n"
            if auth == "open"
            else f"wpa=2\nwpa_passphrase={KEY}\nwpa_key_mgmt=WPA-PSK\nrsn_pairwise=CCMP\n"
        )
    ssid += "-ABSENT" if fault == "ssid" else ""
    base = "ctrl_interface=/run/wpa_supplicant\np2p_disabled=1\nnetwork={\n" + f' ssid="{ssid}"\n'
    security = " key_mgmt=NONE\n"
    if auth == "wpa2":
        key = "Incorrect-Lab-Key-483" if fault == "key" else KEY
        security = f' key_mgmt=WPA-PSK\n proto=RSN\n pairwise=CCMP\n group=CCMP\n psk="{key}"\n'
    return base + security + "}\n"


def parse_status(text):
    result = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError("Duplicate status field")
        result[key] = value
    return result


def association(status, link, value):
    peer = re.search(r"(?m)^Connected to ([0-9a-f:]+) \(on wlan0\)", link, re.IGNORECASE)
    return {
        "completed": status.get("wpa_state") == "COMPLETED",
        "expected_ssid": status.get("ssid") == value["ssid"],
        "same_kernel_peer": bool(
            peer and MAC.fullmatch(peer[1]) and peer[1].lower() == status.get("bssid", "").lower()
        ),
        "expected_key_management": status.get("key_mgmt")
        == ("NONE" if value["auth"] == "open" else "WPA2-PSK"),
        "expected_cipher": value["auth"] == "open"
        or (status.get("pairwise_cipher") == "CCMP" and status.get("group_cipher") == "CCMP"),
    }


def packet_counts(text):
    match = re.search(r"(\d+) (?:packets )?transmitted, (\d+) received", text)
    if not match:
        raise ValueError("The bound ping did not return observable packet counts")
    return int(match[1]), int(match[2])


def run_command(argv, *, check=True, timeout=20):
    return subprocess.run(
        argv,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "LC_ALL": "C"},
    )


def paths(role):
    stem = "h" if role == "ap" else "w"
    return ROOT / (stem + ".conf"), ROOT / (stem + ".pid"), ROOT / (stem + ".log")


def owned_process(role, pid):
    if type(pid) is not int or pid <= 1:
        raise ValueError("Unsafe daemon PID")
    try:
        args = (PROC / str(pid) / "cmdline").read_bytes().split(b"\0")
    except FileNotFoundError:
        return False
    if not args[0]:
        return False
    executable = "hostapd" if role == "ap" else "wpa_supplicant"
    config = str(paths(role)[0]).encode()
    return Path(os.fsdecode(args[0])).name == executable and (
        config in args or b"-c" + config in args
    )


def stop(role):
    _, pidfile, _ = paths(role)
    if not pidfile.exists():
        return
    pid = int(pidfile.read_text().strip())
    if (PROC / str(pid)).exists() and not owned_process(role, pid):
        raise RuntimeError("Refusing to signal a process outside this fixture")
    if owned_process(role, pid):
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 5
        while owned_process(role, pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        if owned_process(role, pid):
            raise RuntimeError("Owned radio daemon did not stop")
    pidfile.unlink(missing_ok=True)


def configure(value, fault):
    text = configuration(value, fault)
    role = value["role"]
    stop(role)
    run_command(["ip", "link", "set", "wlan0", "down"])
    run_command(["ip", "neigh", "flush", "dev", "wlan0"])
    address = TARGET if role == "ap" else CLIENT
    run_command(["ip", "address", "replace", address + "/24", "dev", "wlan0"])
    config, pidfile, logfile = paths(role)
    config.write_text(text)
    config.chmod(0o600)
    run_command(["ip", "link", "set", "wlan0", "up"])
    argv = (
        ["hostapd", "-B", "-P", str(pidfile), "-f", str(logfile), str(config)]
        if role == "ap"
        else [
            "wpa_supplicant",
            "-B",
            "-P" + str(pidfile),
            "-iwlan0",
            "-c" + str(config),
            "-f" + str(logfile),
        ]
    )
    run_command(argv)
    return {"configured": True, "role": role, "auth": value["auth"], "fault": fault}


def interface_ready(value):
    interfaces = json.loads(run_command(["ip", "-j", "address", "show", "dev", "wlan0"]).stdout)
    address = TARGET if value["role"] == "ap" else CLIENT
    assert len(interfaces) == 1 and "UP" in interfaces[0]["flags"]
    assert any(
        item.get("local") == address and item.get("prefixlen") == 24
        for item in interfaces[0]["addr_info"]
    ), "The benchmark radio address must remain configured during every phase"


def snapshot():
    status = parse_status(run_command(["wpa_cli", "-i", "wlan0", "status"]).stdout)
    link = run_command(["iw", "dev", "wlan0", "link"]).stdout
    return status, link


def check(value, fault, expected):
    assert paths(value["role"])[0].read_text() == configuration(value, fault)
    interface_ready(value)
    if value["role"] == "ap":
        status = parse_status(run_command(["hostapd_cli", "-i", "wlan0", "status"]).stdout)
        assert status.get("state") == "ENABLED" and status.get("ssid[0]") == value["ssid"]
        assert status.get("channel") == "6" and MAC.fullmatch(status.get("bssid[0]", ""))
        return {"status": "passed", "role": "ap", "state": "ENABLED"}
    if expected == "down":
        assert fault in ("ssid", "key"), "A negative check needs its explicit controlled fault"
        states = []
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            status, link = snapshot()
            states.append(status.get("wpa_state"))
            assert status.get("wpa_state") != "COMPLETED"
            if fault == "ssid":
                assert not re.search(r"(?m)^Connected to ", link)
            time.sleep(2)
        result = run_command(["ping", "-I", "wlan0", "-c", "3", "-W", "2", TARGET], check=False)
        assert packet_counts(result.stdout) == (3, 0) and result.returncode != 0
        return {
            "status": "passed",
            "role": "client",
            "fault": fault,
            "received": 0,
            "observed_states": states,
        }
    assert fault == "none"
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        status, link = snapshot()
        if all(association(status, link, value).values()):
            result = run_command(["ping", "-I", "wlan0", "-c", "3", "-W", "2", TARGET], check=False)
            if result.returncode == 0 and packet_counts(result.stdout) == (3, 3):
                return {
                    "status": "passed",
                    "role": "client",
                    "auth": value["auth"],
                    "wpa_state": "COMPLETED",
                    "received": 3,
                    "cipher": status.get("pairwise_cipher"),
                }
        time.sleep(2)
    raise TimeoutError("Real association, authentication and radio packet delivery did not recover")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("configure", "check"))
    parser.add_argument("--fault", choices=("none", "ssid", "key"), default="none")
    parser.add_argument("--expect", choices=("up", "down"), default="up")
    args = parser.parse_args()
    if os.geteuid() != 0 or (ROOT / "CML-WIRELESS-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("This command is only for a marked, owned disposable radio guest")
    value = settings(json.loads((ROOT / "wireless.json").read_text()))
    result = (
        configure(value, args.fault)
        if args.action == "configure"
        else check(value, args.fault, args.expect)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
