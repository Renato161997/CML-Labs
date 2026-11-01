"""Network publisher/probes for the isolated signed-event controller fixture."""

import argparse
import http.client
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from controller_contract import decode
from event_gateway import HOST, MARKER, PORT, encode, event, sign

ROOT = Path("/lab")


def wire(raw=None, signature=None, path="/events", method="POST"):
    conn = http.client.HTTPConnection(HOST, PORT, timeout=75)
    headers = {}
    if raw is not None:
        headers = {
            "Content-Type": "application/json",
            "X-CML-Signature": sign(raw) if signature is None else signature,
        }
    try:
        conn.request(method, path, body=raw, headers=headers)
        response = conn.getresponse()
        body = response.read(65537)
        assert len(body) <= 65536 and response.getheader("Content-Type") == "application/json"
        return response.status, decode(body)
    finally:
        conn.close()


def gateway_health():
    status, value = wire(path="/health", method="GET")
    assert (
        status == 200
        and set(value) == {"marker", "pid"}
        and value["marker"] == MARKER
        and value["pid"] > 1
    )
    return value


def send(operation):
    status, value = wire(encode(event(operation)))
    assert status == 200 and value["job"]["status"] == "succeeded" and value["job"]["attempts"] == 1
    assert value["job"]["request_id"] == ("withdraw-1" if operation == "quarantine" else "repair-1")
    return value


def save(value):
    p = ROOT / "event-client-state.json"
    p.write_text(json.dumps(value, sort_keys=True))
    p.chmod(0o600)


def load():
    return decode((ROOT / "event-client-state.json").read_text())


def rejection_cases():
    good = encode(event("quarantine"))
    stale = encode(event("quarantine", int(time.time()) - 120))
    outside = encode({**event("quarantine"), "prefix": "0.0.0.0/0"})
    self_approved = encode({**event("quarantine"), "approved": True})
    duplicate = good[:-1] + b',"device":"OTHER"}'
    return [
        (good, sign(good, b"incorrect-public-key"), 401),
        (good + b" ", sign(good), 401),
        (stale, sign(stale), 422),
        (outside, sign(outside), 422),
        (self_approved, sign(self_approved), 422),
        (duplicate, sign(duplicate), 422),
    ]


def exercise(phase):
    # Registered guest name for the unchanged controller_client.py.
    from client import get, observed, submit
    from controller_contract import GOOD, intent

    if phase == "seed":
        result = submit(intent("install-1"))
        assert result["job"]["attempts"] == 1
        history = get("/v1/history")
        assert len(history["jobs"]) == 1
        observed([GOOD])
        save(
            {
                "history": history,
                "gateway_pid": gateway_health()["pid"],
                "controller_pid": get("/health")["pid"],
            }
        )
        return {"status": "passed", "phase": phase, "real_route_seeded": True, "jobs": 1}
    if phase == "invalids":
        before = get("/v1/history")
        cases = rejection_cases()
        for raw, signature, expected in cases:
            status, value = wire(raw, signature)
            assert status == expected and set(value) == {"error"}
            assert get("/v1/history") == before, "Rejected event changed device-job history"
        time.sleep(3)
        observed([GOOD])
        gateway_health()
        return {
            "status": "passed",
            "phase": phase,
            "wire_rejections": len(cases),
            "history_unchanged": True,
        }
    if phase == "approval-denied":
        before = get("/v1/history")
        status, value = wire(encode(event("quarantine")))
        assert status == 403 and value == {"error": "intent_not_approved"}
        assert get("/v1/history") == before
        observed([GOOD])
        return {
            "status": "passed",
            "phase": phase,
            "valid_signature_is_not_approval": True,
            "history_unchanged": True,
        }
    if phase == "quarantine":
        result = send("quarantine")
        assert result["applied_now"] is True and result["replayed"] is False
        history = get("/v1/history")
        assert len(history["jobs"]) == 2
        observed([], desired=[])
        state = load()
        state["history"] = history
        state["gateway_pid"] = gateway_health()["pid"]
        save(state)
        return {"status": "passed", "phase": phase, "actual_route_withdrawn": True, "jobs": 2}
    if phase == "gateway-down":
        try:
            wire(path="/health", method="GET")
        except ConnectionRefusedError:
            pass
        else:
            raise AssertionError("Stopped gateway did not refuse its listener")
        assert get("/health")["pid"] == load()["controller_pid"]
        assert get("/v1/history") == load()["history"]
        observed([], desired=[])
        return {
            "status": "passed",
            "phase": phase,
            "gateway_listener_refused": True,
            "controller_and_device_preserved": True,
        }
    if phase in ("repeat", "repeat-after-restart"):
        state = load()
        health = gateway_health()
        if phase == "repeat-after-restart":
            assert health["pid"] != state["gateway_pid"]
        else:
            assert health["pid"] == state["gateway_pid"]
        assert get("/health")["pid"] == state["controller_pid"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: send("quarantine"), range(2)))
        assert all(value["replayed"] is True and value["applied_now"] is False for value in results)
        assert get("/v1/history") == state["history"]
        observed([], desired=[])
        return {
            "status": "passed",
            "phase": phase,
            "duplicate_deliveries": 2,
            "committed_event_replayed_without_write": True,
            "history_unchanged": True,
        }
    if phase == "release":
        result = send("release")
        assert result["applied_now"] is True and result["replayed"] is False
        history = get("/v1/history")
        assert len(history["jobs"]) == 3
        assert all(job["status"] == "succeeded" and job["attempts"] == 1 for job in history["jobs"])
        observed([GOOD])
        return {"status": "passed", "phase": phase, "actual_route_recovered": True, "jobs": 3}
    raise ValueError("Unknown event probe phase")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        choices=[
            "seed",
            "invalids",
            "approval-denied",
            "quarantine",
            "gateway-down",
            "repeat",
            "repeat-after-restart",
            "release",
        ],
    )
    phase = parser.parse_args().phase
    if os.geteuid() != 0 or (ROOT / "CML-EVENT-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the isolated event fixture is accepted")
    print(json.dumps(exercise(phase), sort_keys=True))


if __name__ == "__main__":
    main()
