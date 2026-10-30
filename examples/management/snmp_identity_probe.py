"""SNMPv3 view checks with the exact configured lab device identity."""

import argparse
import ipaddress
import json
import re
import subprocess
from pathlib import Path

from snmp_probe import SYSNAME, UPTIME, request


def probe(target, mode, expected_name):
    observations = []

    def observe(oid, predicate, label, **options):
        code, response = request(target, oid, **options)
        passed = bool(predicate(code, response))
        observations.append({"check": label, "passed": passed, "response": response})
        if not passed:
            raise RuntimeError(label + ": " + response)

    uptime = lambda code, text: code == 0 and bool(re.search(r"Timeticks:\s*\(\d+\)", text))
    observe(UPTIME, uptime, "authenticated encrypted uptime")
    if mode == "healthy":
        observe(
            SYSNAME,
            lambda code, text: (
                code == 0
                and bool(re.search(r'STRING:\s*"?' + re.escape(expected_name) + r'"?\s*$', text))
            ),
            "exact configured sysName",
        )
    else:
        observe(
            SYSNAME,
            lambda code, text: (
                code == 0 and bool(re.search(r"No Such (?:Object|Instance)", text, re.IGNORECASE))
            ),
            "identity excluded by view",
        )
    observe(
        UPTIME,
        lambda code, text: (
            code != 0
            and bool(re.search(r"authentication failure|Timeout: No Response", text, re.IGNORECASE))
        ),
        "wrong key rejected",
        wrong_auth=True,
    )
    observe(UPTIME, uptime, "valid credentials still work")
    return {"status": "passed", "mode": mode, "observations": observations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("healthy", "restricted"))
    args = parser.parse_args()
    config = json.loads(Path("/lab/snmp.json").read_text(encoding="utf-8"))
    if ipaddress.ip_address(config["target"]) not in ipaddress.ip_network("198.18.0.0/15"):
        parser.error("Only isolated benchmark-address fixtures are supported")
    try:
        report = probe(config["target"], args.mode, config["expected_sysname"])
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
