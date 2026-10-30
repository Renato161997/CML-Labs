"""Observe disposable lab SSH policy; never print session output or credentials."""

import argparse
import ipaddress
import json
import re
import subprocess

from ssh_probe import DEMO_PASSWORD, session


def assess(mode, code, output):
    if mode == "denied":
        return {
            "session_rejected": code != 0,
            "transport_policy_rejection": bool(
                re.search(r"connection (?:closed|reset|refused|timed out)", output, re.IGNORECASE)
            ),
            "not_an_authentication_or_host_key_failure": not bool(
                re.search(
                    r"permission denied|authentication failed|identification has changed"
                    r"|host key verification failed|current privilege level|R1[>#]",
                    output,
                    re.IGNORECASE,
                )
            ),
        }
    if mode == "elevated":
        return {
            "authenticated_session": code == 0,
            "privilege_fifteen": bool(re.search(r"Current privilege level is\s+15\b", output)),
            "configuration_mode_access": bool(re.search(r"(?m)^R1\(config\)#", output)),
        }
    raise ValueError("Unknown exercise policy mode")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("denied", "elevated"))
    parser.add_argument("--host", default="198.18.0.1")
    args = parser.parse_args()
    address = ipaddress.ip_address(args.host)
    if address not in ipaddress.ip_network("198.18.0.0/15"):
        parser.error("Only isolated benchmark-address fixtures are supported")
    commands = ["terminal length 0", "show privilege"]
    if args.mode == "elevated":
        commands += ["configure terminal", "end"]
    commands.append("exit")
    try:
        code, output = session(str(address), DEMO_PASSWORD, commands)
        checks = assess(args.mode, code, output)
    except subprocess.TimeoutExpired:
        checks = {"probe_finished_with_observable_result": False}
    passed = all(checks.values())
    print(json.dumps({"passed": passed, "mode": args.mode, "checks": checks}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
