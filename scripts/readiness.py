"""Separate a running emulator from an interactively verified guest console."""

import re
import time


def establish_ios_prompt(label, prompt, send, read, *, timeout=240):
    """Wait for the named guest CLI before sending privileged-mode commands."""
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 1 <= timeout <= 600
    ):
        raise ValueError("IOS startup timeout must be between 1 and 600 seconds")
    deadline = time.monotonic() + timeout
    pattern = re.compile(r"(?m)^" + re.escape(label) + r"[>#]\s*$")
    while not pattern.search(prompt.replace("\r", "")):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Named IOS console prompt was not ready within {timeout} seconds")
        send("\r")
        prompt += read(min(8, remaining))
    return prompt


def establish_ios_privilege(label, send, read, *, timeout=45):
    """Negotiate privilege with fresh output, tolerating delayed boot chatter."""
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 90:
        raise ValueError("IOS privilege timeout must be between 1 and 90 seconds")
    deadline = time.monotonic() + timeout
    named = re.compile(r"(?m)^" + re.escape(label) + r"([>#])\s*$")
    send("\r")
    output = ""
    sent_enable = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Fresh privileged IOS console prompt was not established")
        output += read(min(8, remaining))
        normalized = output.replace("\r", "")
        if re.search(r"(?im)^\s*password:\s*$", normalized):
            raise PermissionError("IOS console requires an enable credential")
        matches = list(named.finditer(normalized))
        if not matches:
            if not sent_enable:
                # A late boot message can append [OK] to the visible user
                # prompt. Request a clean redraw before issuing enable.
                send("\r")
            continue
        if matches[-1].group(1) == "#":
            return output
        if not sent_enable:
            send("enable\r")
            sent_enable = True
            output = ""


def running_node_states(nodes):
    """Return observed states only when every expected process is running.

    STARTED alone is not a boot or functional pass. Its console must still be
    established, and every acceptance check must subsequently succeed.
    """
    states = {}
    for node in nodes:
        state = str(node.state)
        if state not in ("BOOTED", "STARTED"):
            return None
        if node.label in states:
            raise RuntimeError("Duplicate node label in process-state response")
        states[node.label] = state
    return states or None


def verify_unconfirmed_consoles(states, connect):
    """Connect must raise unless the expected interactive guest prompt is ready."""
    verified = []
    for label, state in states.items():
        if state not in ("BOOTED", "STARTED"):
            raise RuntimeError("Cannot establish readiness for a stopped or queued process")
        if state == "STARTED":
            connect(label)
            verified.append(label)
    return verified
