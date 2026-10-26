"""Separate a running emulator from an interactively verified guest console."""


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
