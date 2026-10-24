"""Run real HTTP acceptance checks against the isolated receiver."""

import json
import os
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def run(url, token):
    deadline = time.monotonic() + 5
    while True:
        try:
            with urlopen(url + "/health", timeout=0.5) as response:
                assert json.load(response) == {"status": "ok"}, "Unexpected health response"
            break
        except (URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise RuntimeError("Receiver did not become ready within five seconds") from None
            time.sleep(0.1)
    event = {
        "event_id": secrets.token_hex(12),
        "device": "R1",
        "interface": "Loopback0",
        "enabled": True,
    }
    checks = []

    def post(value, expected, label, auth=token):
        request = Request(
            url + "/events",
            json.dumps(value).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + auth},
        )
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            payload = json.loads(response.read())
            assert response.code == expected, (label, response.code)
            assert not payload.get("applied", False), "This example must never claim device changes"
        checks.append(label)

    post(event, 401, "unauthorized request rejected", auth="wrong-token")
    post(event, 202, "valid intent accepted")
    post(event, 200, "duplicate request is idempotent")
    post(dict(event, enabled=False), 409, "conflicting event ID rejected")
    post(
        dict(event, event_id=secrets.token_hex(12), interface="not-a-real-interface"),
        422,
        "invalid interface rejected",
    )
    post(
        dict(event, event_id=secrets.token_hex(12), enabled="true"), 422, "string boolean rejected"
    )
    print(json.dumps({"passed": len(checks), "checks": checks, "device_changes": 0}))
    return checks


if __name__ == "__main__":
    run(
        os.environ.get("LAB_WEBHOOK_URL", "http://127.0.0.1:8080"), os.environ["LAB_WEBHOOK_SECRET"]
    )
