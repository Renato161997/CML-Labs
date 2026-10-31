"""Establish an identifiable root shell on a disposable CML server container.

The prompt is only a framing aid. Real UID zero is checked before changing PS1;
neither a root-looking prompt nor an emulator STARTED state proves readiness.
"""

import json
import re
import time

from console_protocol import response_complete

NATIVE_LINUX = frozenset(
    {"net-tools", "radius", "syslog", "tacplus", "cml-labs-toolbox", "cml-labs-inspection"}
)
NATIVE_CONSOLE_PORT = {
    "net-tools": 0,
    "radius": 1,
    "syslog": 1,
    "tacplus": 1,
    "cml-labs-toolbox": 0,
    "cml-labs-inspection": 0,
}
ROOT_PROMPT = r"(?:root@[^:\n]+:[^\n#]*#|/[^\n#]*#|bash-[\d.]+#)"


def _clean(text):
    return re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text).replace("\r", "")


def _after_echo(output, command):
    match = re.search(rf"(?m)^(?:{ROOT_PROMPT}[ \t]*)?{re.escape(command)}[ \t]*$", _clean(output))
    if not match:
        raise RuntimeError("Native Linux command echo was not complete")
    return _clean(output)[match.end() :]


def establish_linux_shell(label, send, read):
    """Only call on an owned lab's native server console, never a host terminal."""
    if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", label):
        raise ValueError("Unsafe native Linux console label")
    send("\rid -u\r")
    tail = _after_echo(read(8), "id -u")
    uid = re.search(r"(?m)^0[ \t]*$", tail)
    if not uid or not re.search(rf"(?m)^{ROOT_PROMPT}[ \t]*$", tail[uid.end() :]):
        raise RuntimeError("Native Linux console did not establish a real UID-zero shell")

    command = "export PS1='root@" + label + ":~# '"
    send("\r" + command + "\r")
    tail = _after_echo(read(8), command)
    if not re.search(rf"(?m)^root@{re.escape(label)}:~#[ \t]*$", tail):
        raise RuntimeError("Native Linux prompt could not be established")


def establish_ubuntu_shell(label, initial, send, read, *, timeout=240):
    """Wait through cloud-final/getty replacement before accepting a root shell.

    Only the read-only cloud-init status query may be reissued after an
    interrupted echo. Functional/configuration commands keep strict framing.
    """
    if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", label):
        raise ValueError("Unsafe Ubuntu console label")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 1 <= timeout <= 600
    ):
        raise ValueError("Ubuntu startup timeout must be between 1 and 600 seconds")
    deadline = time.monotonic() + timeout
    prompt = re.compile(rf"(?m)^root@{re.escape(label)}:[^\n#]*#[ \t]*$")
    current = _clean(initial)
    command = "cloud-init status --format json"
    while time.monotonic() < deadline:
        if not prompt.search(current):
            send("\r")
            current += _clean(read(min(8, max(0.1, deadline - time.monotonic()))))
            continue
        send("\r" + command + "\r")
        output = ""
        while time.monotonic() < deadline:
            output += read(min(8, max(0.1, deadline - time.monotonic())))
            if response_complete(output, command, label) or prompt.search(_clean(output)):
                break
        current = _clean(output)
        if response_complete(output, command, label):
            tail = _after_echo(output, command)
            start = re.search(r"(?m)^\s*\{", tail)
            try:
                if not start:
                    raise ValueError("Missing status JSON")
                status, _ = json.JSONDecoder().raw_decode(tail[start.start() :].lstrip())
                if not isinstance(status, dict):
                    raise TypeError("Invalid status object")
            except (ValueError, TypeError) as error:
                raise RuntimeError("Cloud-init did not return a valid status object") from error
            if status.get("status") == "done" and not status.get("errors"):
                establish_linux_shell(label, send, read)
                return
            if status.get("status") not in ("running", "not started") or status.get("errors"):
                raise RuntimeError("Cloud-init did not complete successfully")
        read(min(2, max(0.1, deadline - time.monotonic())))
    raise TimeoutError("Ubuntu cloud-init/root console did not become ready")
