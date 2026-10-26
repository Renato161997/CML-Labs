"""Real Net-SNMP probes for the isolated SNMPv3 authPriv exercise.

All credentials below are deliberately public teaching fixtures. No installation,
network scan or production endpoint discovery is performed by this client.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SYSNAME = ".1.3.6.1.2.1.1.5.0"
UPTIME = ".1.3.6.1.2.1.1.3.0"
AUTH = "Cml-Snmp-Auth-Only-983"
PRIV = "Cml-Snmp-Priv-Only-984"


def request(target, oid, *, wrong_auth=False):
    command = [
        "snmpget",
        "-v3",
        "-l",
        "authPriv",
        "-u",
        "CML-SNMP",
        "-a",
        "SHA",
        "-A",
        "Wrong-auth-only-999" if wrong_auth else AUTH,
        "-x",
        "AES",
        "-X",
        PRIV,
        "-t",
        "2",
        "-r",
        "0",
        "-On",
        target,
        oid,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
    return result.returncode, (result.stdout + result.stderr).strip()


def probe(target, mode):
    observations = []

    def observe(oid, predicate, label, **options):
        code, output = request(target, oid, **options)
        passed = bool(predicate(code, output))
        observations.append(
            {"check": label, "passed": passed, "returncode": code, "response": output}
        )
        if not passed:
            raise RuntimeError("Network assertion failed: " + label)

    observe(
        UPTIME,
        lambda c, s: c == 0 and bool(re.search(r"Timeticks:\s*\(\d+\)", s)),
        "authenticated encrypted uptime",
    )
    if mode == "healthy":
        observe(
            SYSNAME,
            lambda c, s: c == 0 and bool(re.search(r'STRING:\s*"?R1"?\s*$', s)),
            "visible sysName",
        )
    else:
        observe(
            SYSNAME,
            lambda c, s: (
                c == 0 and bool(re.search(r"No Such (?:Object|Instance)", s, re.IGNORECASE))
            ),
            "view excludes sysName",
        )
    observe(
        UPTIME,
        lambda c, s: (
            c != 0
            and bool(re.search(r"authentication failure|Timeout: No Response", s, re.IGNORECASE))
        ),
        "wrong authentication key is rejected",
        wrong_auth=True,
    )
    observe(
        UPTIME,
        lambda c, s: c == 0 and bool(re.search(r"Timeticks:\s*\(\d+\)", s)),
        "agent still answers valid credentials",
    )
    return {"status": "passed", "mode": mode, "target": target, "observations": observations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("healthy", "restricted"))
    args = parser.parse_args()
    config = json.loads(Path("/lab/snmp.json").read_text(encoding="utf-8"))
    try:
        report = probe(config["target"], args.mode)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
