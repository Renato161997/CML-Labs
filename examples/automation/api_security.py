"""Wire-level negative controls for the isolated device-backed teaching API."""

import argparse
import http.client
import json
import os
import time
from pathlib import Path

from controller_contract import GOOD, MARKER, TOKEN, approvals, decode, intent

ROOT = Path("/lab")
AUTH = ("Authorization", "Bearer " + TOKEN)


def cases():
    valid = json.dumps(intent("unapproved-2")).encode()
    invalid = [
        {**intent("invalid-2"), "approved": True},
        {**intent("invalid-2"), "prefix": "203.0.113.5/32"},
        {**intent("invalid-2"), "state": True},
    ]
    result = [
        ("missing-read-token", "GET", "/v1/device", [], None, 401, "authentication_required"),
        (
            "wrong-read-token",
            "GET",
            "/v1/device",
            [("Authorization", "Bearer wrong-public-fixture")],
            None,
            401,
            "authentication_required",
        ),
        (
            "ambiguous-authentication",
            "GET",
            "/v1/device",
            [AUTH, ("Authorization", "Bearer wrong-public-fixture")],
            None,
            401,
            "authentication_required",
        ),
        (
            "duplicate-valid-authentication",
            "GET",
            "/v1/device",
            [AUTH, AUTH],
            None,
            401,
            "authentication_required",
        ),
        (
            "missing-write-token",
            "POST",
            "/v1/route-intents",
            [],
            valid,
            401,
            "authentication_required",
        ),
        (
            "unapproved-intent",
            "POST",
            "/v1/route-intents",
            [AUTH],
            valid,
            403,
            "intent_not_approved",
        ),
    ]
    for index, value in enumerate(invalid):
        result.append(
            (
                "invalid-intent-" + str(index),
                "POST",
                "/v1/route-intents",
                [AUTH],
                json.dumps(value).encode(),
                422,
                "invalid_intent",
            )
        )
    duplicate = valid.replace(b'{"request_id":', b'{"request_id":"duplicate-2","request_id":', 1)
    result.extend(
        [
            (
                "duplicate-json-key",
                "POST",
                "/v1/route-intents",
                [AUTH],
                duplicate,
                422,
                "invalid_intent",
            ),
            (
                "wrong-media-type",
                "POST",
                "/v1/route-intents",
                [AUTH, ("Content-Type", "text/plain")],
                valid,
                415,
                "json_required",
            ),
            (
                "duplicate-media-type",
                "POST",
                "/v1/route-intents",
                [AUTH, ("Content-Type", "application/json"), ("Content-Type", "application/json")],
                valid,
                415,
                "json_required",
            ),
            (
                "duplicate-body-length",
                "POST",
                "/v1/route-intents",
                [AUTH, ("Content-Length", str(len(valid))), ("Content-Length", "0")],
                valid,
                400,
                "invalid_body_framing",
            ),
            (
                "conflicting-body-framing",
                "POST",
                "/v1/route-intents",
                [AUTH, ("Transfer-Encoding", "chunked")],
                valid,
                400,
                "invalid_body_framing",
            ),
            ("oversize-body", "POST", "/v1/route-intents", [AUTH], b"x" * 4097, 413, "body_limit"),
        ]
    )
    return result


def wire(method, path, headers, body):
    connection = http.client.HTTPConnection("198.18.1.1", 8080, timeout=65)
    try:
        connection.putrequest(method, path)
        for name, value in headers:
            connection.putheader(name, value)
        names = {name.lower() for name, _ in headers}
        if body is not None:
            if "content-type" not in names:
                connection.putheader("Content-Type", "application/json")
            if "content-length" not in names:
                connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        response = connection.getresponse()
        raw = response.read(65537)
        assert len(raw) <= 65536 and response.getheader("Content-Type") == "application/json"
        return response.status, decode(raw)
    finally:
        connection.close()


def rejection(status, value, expected_status, expected_error):
    assert status == expected_status, "The expected rejection was not observed"
    assert value == {"error": expected_error}, "Rejection exposed unexpected response data"


def policy(enabled):
    path = ROOT / "controller-approvals.json"
    if path.is_symlink() or not path.is_file():
        raise PermissionError("Only the existing own fixture policy may be changed")
    expected = [] if enabled else approvals()
    if decode(path.read_text()) != expected:
        raise ValueError("Unexpected existing policy; refuse to overwrite it")
    temporary = ROOT / "controller-approvals.next"
    with temporary.open("x", encoding="utf-8") as output:
        json.dump(approvals() if enabled else [], output, sort_keys=True)
    temporary.chmod(0o600)
    temporary.replace(path)
    return {"status": "passed", "policy_enabled": enabled}


def exercise(phase):
    # Only CLIENT needs these imports; TOOLS uses the separate local policy CLI.
    from client import get, observed, request

    before = get("/v1/history")
    if phase == "approval-denied":
        status, value = request("POST", "/v1/route-intents", intent("withdraw-1", "absent"))
        rejection(status, value, 403, "intent_not_approved")
        assert get("/v1/history") == before
        observed([GOOD])
        return {"status": "passed", "approved_credential_is_not_approval": True}
    backend_down = phase == "matrix-down"
    windows = 0
    if not backend_down:
        time.sleep(3)
        observed([GOOD])
        windows += 1
    for index, (name, method, path, headers, body, expected, error) in enumerate(cases(), 1):
        try:
            status, value = wire(method, path, headers, body)
            rejection(status, value, expected, error)
            assert get("/v1/history") == before, "Rejected input created a job or history event"
            if backend_down:
                status, value = request("GET", "/v1/device")
                assert (
                    status == 503
                    and value["error"] == "backend_unavailable"
                    and "facts" not in value
                )
            elif index % 5 == 0 or index == len(cases()):
                # Avoid a fresh SSH/NETCONF session for every HTTP rejection.
                time.sleep(3)
                observed([GOOD])
                windows += 1
        except Exception as failure:
            failure.add_note("Wire rejection case: " + name)
            raise
    assert get("/health")["marker"] == MARKER
    return {
        "status": "passed",
        "wire_rejections": len(cases()),
        "history_unchanged": True,
        "backend_down": backend_down,
        "actual_device_rechecked": windows > 0,
        "device_observation_windows": windows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=("matrix", "matrix-down", "approval-denied", "policy-off", "policy-on")
    )
    phase = parser.parse_args().phase
    if os.geteuid() != 0 or (ROOT / "CML-CONTROLLER-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the marked disposable controller fixture is accepted")
    value = policy(phase == "policy-on") if phase.startswith("policy-") else exercise(phase)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
