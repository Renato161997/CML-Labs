"""Exercise-only OpenSSH probe; no production credentials or private keys."""

import argparse
import ipaddress
import json
import os
import re
import socket
import subprocess
from pathlib import Path

DEMO_PASSWORD = "CML-LAB-ONLY"


def session(host, password, commands):
    environment = {
        **os.environ,
        "SSH_ASKPASS_REQUIRE": "force",
        "SSH_ASKPASS": "/opt/cml-management/askpass.sh",
        "CML_TEST_PASSWORD": password,
    }
    args = [
        "ssh",
        "-tt",
        "-F",
        "none",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "UserKnownHostsFile=/tmp/cml-management-known-hosts",
        "-o",
        "PreferredAuthentications=password",
        "-o",
        "PubkeyAuthentication=no",
        "-o",
        "NumberOfPasswordPrompts=1",
        "-o",
        "ConnectTimeout=5",
        f"viewer@{host}",
    ]
    result = subprocess.run(
        args,
        input="\r".join(commands) + "\r",
        capture_output=True,
        text=True,
        timeout=12,
        env=environment,
        start_new_session=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def closed(host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return False
    except OSError:
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="198.18.0.1")
    parser.add_argument("--banner", default="CML-SSH-LAB")
    args = parser.parse_args()
    address = ipaddress.ip_address(args.host)
    if address not in ipaddress.ip_network("198.18.0.0/15"):
        parser.error("This fixture is restricted to its isolated benchmark-address lab")
    commands = [
        "terminal length 0",
        "show privilege",
        "show clock",
        "configure terminal",
        "exit",
        "exit",
    ]
    good_code, good_output = session(str(address), DEMO_PASSWORD, commands)
    bad_code, bad_output = session(str(address), "INCORRECT-LAB-PASSWORD", ["exit"])
    checks = {
        "valid_password_session": good_code == 0,
        "viewer_privilege_one": bool(re.search(r"Current privilege level is\s+1\b", good_output)),
        "exec_clock_response": bool(re.search(r"\d{2}:\d{2}:\d{2}", good_output)),
        "configuration_denied": bool(
            re.search(
                r"Invalid input|not authorized|authorization failed", good_output, re.IGNORECASE
            )
        ),
        "login_banner": args.banner in good_output,
        "wrong_password_rejected": bad_code != 0
        and bool(re.search(r"Permission denied|Authentication failed", bad_output, re.IGNORECASE)),
        "telnet_closed": closed(str(address), 23),
        "http_closed": closed(str(address), 80),
        "https_closed": closed(str(address), 443),
    }
    if not all(checks.values()):
        Path("/tmp/cml-management-debug.json").write_text(
            json.dumps(
                {
                    "good_code": good_code,
                    "good_output": good_output,
                    "bad_code": bad_code,
                    "bad_output": bad_output,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"passed": all(checks.values()), "checks": checks}, sort_keys=True))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
