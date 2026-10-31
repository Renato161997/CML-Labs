"""Exercise the controller over its real isolated northbound Ethernet link."""

import argparse
import http.client
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from controller_contract import BAD, GOOD, MARKER, TOKEN, decode, intent

ROOT = Path("/lab")
HOST = "198.18.1.1"
PORT = 8080


def request(method, path, value=None, token=TOKEN):
    connection = http.client.HTTPConnection(HOST, PORT, timeout=65)
    headers = {"Authorization": "Bearer " + token}
    body = None
    if value is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(value).encode()
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read(65537)
        assert len(raw) <= 65536 and response.getheader("Content-Type") == "application/json"
        return response.status, decode(raw)
    finally:
        connection.close()


def get(path):
    status, value = request("GET", path)
    assert status == 200, value
    return value


def submit(value):
    status, result = request("POST", "/v1/route-intents", value)
    assert status == 200 and result["job"]["status"] == "succeeded", result
    return result


def observed(hops, desired=None):
    value = get("/v1/device")
    assert value["facts"]["hostname"] == "API" and value["facts"]["ipv4"] == "198.18.0.1"
    expected = [GOOD] if desired is None else desired
    assert value["configured_next_hops"] == hops and value["desired_next_hops"] == expected
    assert value["drift"] == (hops != expected)
    assert value["off_link_next_hops"] == ([BAD] if hops == [BAD] else [])
    return value


def baseline():
    health = get("/health")
    assert health["kind"] == "service" and health["marker"] == MARKER and health["pid"] > 1
    before = get("/v1/history")
    assert request("GET", "/v1/device", token="incorrect-public-fixture")[0] == 401
    assert request("POST", "/v1/route-intents", intent("unapproved-1"))[0] == 403
    for invalid in [
        {**intent("invalid-1"), "approved": True},
        {**intent("invalid-1"), "prefix": "203.0.113.1/32"},
        {**intent("invalid-1"), "state": True},
    ]:
        assert request("POST", "/v1/route-intents", invalid)[0] == 422
    assert get("/v1/history") == before, "Rejected requests must not create jobs or device writes"
    result = submit(intent("install-1"))
    assert result["job"]["attempts"] == 1
    after = get("/v1/history")
    assert len(after["jobs"]) == 1
    assert request("POST", "/v1/route-intents", intent("install-1", "absent"))[0] == 409
    assert get("/v1/history") == after
    observed([GOOD])
    (ROOT / "controller-client-state.json").write_text(
        json.dumps({"pid": health["pid"], "history": after}, sort_keys=True)
    )
    return {
        "status": "passed",
        "phase": "baseline",
        "approved_job": "install-1",
        "invalid_requests_rejected": True,
    }


def run(phase):
    if phase == "baseline":
        return baseline()
    if phase == "down":
        try:
            request("GET", "/health")
        except ConnectionRefusedError:
            return {"status": "passed", "phase": "down", "listener_refused": True}
        raise AssertionError("The stopped controller still accepts HTTP requests")
    if phase == "persistence":
        saved = decode((ROOT / "controller-client-state.json").read_text())
        health, history = get("/health"), get("/v1/history")
        assert health["pid"] != saved["pid"] and health["marker"] == MARKER
        assert history["events"][: len(saved["history"]["events"])] == saved["history"]["events"]
        for job in saved["history"]["jobs"]:
            assert (
                next(row for row in history["jobs"] if row["request_id"] == job["request_id"])
                == job
            )
        replay = submit(intent("install-1"))
        assert replay["replayed"] and not replay["applied_now"]
        assert get("/v1/history") == history
        observed([GOOD])
        return {
            "status": "passed",
            "phase": phase,
            "new_process": True,
            "durable_job_replayed_without_write": True,
        }
    if phase == "backend-down":
        assert get("/health")["marker"] == MARKER
        history = get("/v1/history")
        status, value = request("GET", "/v1/device")
        assert status == 503 and value["error"] == "backend_unavailable" and "facts" not in value
        assert get("/v1/history") == history
        return {"status": "passed", "phase": phase, "unavailable_is_not_empty_inventory": True}
    if phase in ("healthy", "drift", "offlink"):
        hops = {"healthy": [GOOD], "drift": [], "offlink": [BAD]}[phase]
        actual = observed(hops)
        return {
            "status": "passed",
            "phase": phase,
            "actual_next_hops": hops,
            "drift": actual["drift"],
            "off_link_next_hops": actual["off_link_next_hops"],
        }
    if phase == "repair":
        result = submit(intent("repair-1"))
        assert result["applied_now"] and not result["replayed"]
        observed([GOOD])
        return {"status": "passed", "phase": phase, "actual_route_reconciled": True}
    if phase == "rollback":
        status, value = request("POST", "/v1/route-intents", intent("rollback-1", "absent"))
        assert status == 502 and value["error"] == "operation_failed"
        job = value["job"]
        assert (
            job["status"] == "failed"
            and job["rollback_verified"] is True
            and job["error_class"] == "FixtureConfirmationFailure"
        )
        history = get("/v1/history")
        events = [item for item in history["events"] if item["request_id"] == "rollback-1"]
        assert (
            next(item for item in events if item["phase"] == "device_confirmed")["detail"]["hops"]
            == []
        )
        assert events[-1]["phase"] == "failed" and events[-1]["detail"]["rollback_verified"] is True
        observed([GOOD])
        return {
            "status": "passed",
            "phase": phase,
            "actual_withdrawal_read_back": True,
            "rollback_verified": True,
        }
    if phase == "concurrent":
        with ThreadPoolExecutor(max_workers=2) as executor:
            values = list(executor.map(lambda _: submit(intent("withdraw-1", "absent")), range(2)))
        assert sum(value["applied_now"] for value in values) == 1
        assert sum(value["replayed"] for value in values) == 1
        history = get("/v1/history")
        jobs = [row for row in history["jobs"] if row["request_id"] == "withdraw-1"]
        assert len(jobs) == 1 and jobs[0]["attempts"] == 1
        phases = [item["phase"] for item in history["events"] if item["request_id"] == "withdraw-1"]
        assert phases == ["pending", "observed_before", "device_confirmed", "committed"]
        observed([], [])
        return {"status": "passed", "phase": phase, "fresh_operation": 1, "duplicate_replay": 1}
    raise ValueError("Unexpected client exercise phase")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        choices=(
            "baseline",
            "down",
            "persistence",
            "healthy",
            "drift",
            "offlink",
            "repair",
            "rollback",
            "concurrent",
            "backend-down",
        ),
    )
    args = parser.parse_args()
    if os.geteuid() != 0 or (ROOT / "CML-CONTROLLER-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the marked disposable controller client is accepted")
    print(json.dumps(run(args.phase), sort_keys=True))


if __name__ == "__main__":
    main()
