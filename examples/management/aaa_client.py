"""Correct public fixture credentials must fail when the AAA relationship breaks."""

import json
import re
import subprocess

from ssh_probe import DEMO_PASSWORD, closed, session


def rejected(code, output):
    return (
        code != 0
        and bool(re.search(r"permission denied|authentication failed", output, re.IGNORECASE))
        and not re.search(
            r"identification has changed|host key verification failed|current privilege level",
            output,
            re.IGNORECASE,
        )
    )


def main():
    host = "198.18.0.1"
    checks = {"ssh_transport_available": not closed(host, 22)}
    try:
        code, output = session(host, DEMO_PASSWORD, ["show privilege", "exit"])
        checks["correct_fixture_password_rejected"] = rejected(code, output)
    except subprocess.TimeoutExpired:
        checks["observable_authentication_rejection"] = False
    passed = all(checks.values())
    print(json.dumps({"passed": passed, "checks": checks}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
