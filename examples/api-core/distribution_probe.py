"""Verify actual frontend/backend responses, scaling and bounded failover."""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

BASE = "http://198.18.0.1:8080"
UPSTREAMS = ("http://198.18.1.2:8080", "http://198.18.1.3:8080")


def request(path, body=None):
    headers = {"X-Lab-Control": "public-training-fixture"} if body else {}
    data = json.dumps(body).encode() if body else None
    try:
        response = build_opener(ProxyHandler({})).open(
            Request(BASE + path, data=data, headers=headers), timeout=4
        )
    except HTTPError as error:
        response = error
    with response:
        return response.code, json.load(response)


def run(phase, parallel=False):
    assert request("/health") == (200, {"service": "frontend"})
    started = time.monotonic()
    count = 16 if parallel else 6
    with ThreadPoolExecutor(max_workers=4 if parallel else 1) as executor:
        replies = list(executor.map(lambda _: request("/resource/1"), range(count)))
    if phase == "all-down":
        assert all(
            code == 503 and body == {"error": "no healthy backend", "attempts": 2}
            for code, body in replies
        )
        assert time.monotonic() - started < count * 3.5
        observed = []
    else:
        assert all(
            code == 200 and body["data"] == {"id": 1, "revision": 1} for code, body in replies
        )
        observed = sorted({body["backend"] for _, body in replies})
        expected = (
            [UPSTREAMS[1]]
            if phase == "first-down"
            else [UPSTREAMS[0]]
            if phase in ("first-only", "scale-in")
            else list(UPSTREAMS)
        )
        assert observed == expected, (observed, expected)
        assert all(1 <= body["attempts"] <= 2 for _, body in replies)
    return {
        "status": "passed",
        "phase": phase,
        "responses": count,
        "backends": observed,
        "concurrent_workers": 4 if parallel else 1,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        nargs="?",
        choices=("baseline", "first-down", "all-down", "first-only", "scale-in", "recovered"),
    )
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--pool", choices=("one", "two"))
    args = parser.parse_args()
    if args.pool:
        selected = list(UPSTREAMS[:1] if args.pool == "one" else UPSTREAMS)
        assert request("/pool", {"upstreams": selected}) == (200, {"upstreams": selected})
        print(json.dumps({"status": "configured", "pool_size": len(selected)}))
    else:
        if not args.phase:
            parser.error("phase is required")
        print(json.dumps(run(args.phase, args.parallel), sort_keys=True))
