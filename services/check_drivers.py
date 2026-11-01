"""Recognize wired drivers without attaching or sending to any network device."""

import re
import subprocess
import tempfile
from pathlib import Path


def hostapd_probe(driver, folder):
    config = folder / (driver + ".conf")
    config.write_text(
        f"driver={driver}\ninterface=cml-missing\nssid=CML-BUILD-ONLY\nieee8021x=1\neap_server=1\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["hostapd", "-dd", str(config)], check=False, capture_output=True, text=True, timeout=5
    )
    return result.returncode, result.stdout + result.stderr


def main():
    supplicant = subprocess.run(
        ["wpa_supplicant", "-h"], check=False, capture_output=True, text=True, timeout=5
    )
    assert re.search(r"(?m)^\s*wired\s*=", supplicant.stdout + supplicant.stderr), (
        "Supplicant does not advertise its wired driver"
    )
    # hostapd help does not provide the same registry listing as the supplicant.
    # Its real driver-init diagnostic must identify a deliberately absent NIC.
    with tempfile.TemporaryDirectory() as temporary:
        code, output = hostapd_probe("wired", Path(temporary))
        bad_code, bad_output = hostapd_probe("cml-unknown", Path(temporary))
    print("HOSTAPD_WIRED_PROBE\n" + output)
    assert bad_code != 0 and "invalid/unknown driver" in bad_output.lower(), (
        "Unknown-driver negative control did not fail as expected"
    )
    assert code != 0 and "invalid/unknown driver" not in output.lower(), (
        "Hostapd did not recognize wired"
    )
    assert "cml-missing" in output and re.search(
        r"(?i)(wired.*(?:init|interface|ifindex)|could not read interface|no such device)",
        output,
    ), "Hostapd did not reach the wired interface initialization path"
    print("WIRED_DRIVERS_PRESENT")


if __name__ == "__main__":
    main()
