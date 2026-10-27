"""Establish an identifiable root shell on a disposable CML server container.

The prompt is only a framing aid. Real UID zero is checked before changing PS1;
neither a root-looking prompt nor an emulator STARTED state proves readiness.
"""

import re

NATIVE_LINUX = frozenset({"net-tools", "radius", "syslog", "tacplus", "cml-labs-toolbox"})
NATIVE_CONSOLE_PORT = {
    "net-tools": 0,
    "radius": 1,
    "syslog": 1,
    "tacplus": 1,
    "cml-labs-toolbox": 0,
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
