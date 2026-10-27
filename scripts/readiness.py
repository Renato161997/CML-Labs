"""Separate a running emulator from an interactively verified guest console."""

import re
import time


def establish_ios_prompt(label, prompt, send, read):
    """Wait for the named guest CLI before sending privileged-mode commands."""
    deadline = time.monotonic() + 240
    pattern = re.compile(r"(?m)^" + re.escape(label) + r"[>#]\s*$")
    while not pattern.search(prompt.replace("\r", "")):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Named IOS console prompt was not ready within 240 seconds")
        send("\r")
        prompt += read(min(8, remaining))
    return prompt


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
