"""Real HTTP assertions for the isolated, vendor-neutral API training service."""

import argparse
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

FAULTS = {
    "pagination": "cursor-loop",
    "errors": "unavailable",
    "rate": "always-throttle",
    "cache": "stale-etag",
    "telemetry": "no-trace",
    "database": "read-only",
}


class Client:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.opener = build_opener(ProxyHandler({}))

    def request(self, path, body=None, headers=None, raw=None):
        headers = dict(headers or {})
        data = json.dumps(body).encode() if body is not None else raw
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base + path, data=data, headers=headers)
        try:
            response = self.opener.open(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            content = response.read()
            return response.code, dict(response.headers), json.loads(content) if content else None

    def control(self, mode):
        assert (
            self.request("/control", {"mode": mode}, {"X-Lab-Control": "public-training-fixture"})[
                0
            ]
            == 200
        )

    def retry(self, path):
        statuses = []
        started = time.monotonic()
        for attempt in range(3):
            code, headers, body = self.request(path)
            statuses.append(code)
            if code not in (429, 503) or attempt == 2:
                return code, body, statuses, time.monotonic() - started
            delay = min(2, max(0.05, float(headers.get("Retry-After", "0.05"))))
            time.sleep(delay)
        raise AssertionError("unreachable")

    def page_all(self):
        offset, seen, items = 0, set(), []
        for _ in range(10):
            if offset in seen:
                raise RuntimeError("pagination cycle detected")
            seen.add(offset)
            code, _, data = self.request(f"/items?offset={offset}&limit=3")
            assert code == 200 and isinstance(data["items"], list)
            items.extend(item["id"] for item in data["items"])
            offset = data["next"]
            if offset is None:
                assert len(items) == len(set(items))
                return items
        raise RuntimeError("pagination request budget exhausted")


def run(base, scenario, phase, cache_file):
    client = Client(base)
    assert client.request("/health")[0] == 200, "health path must stay available"
    fault = phase == "fault"
    checks = ["separate health endpoint reachable"]
    if scenario == "pagination":
        if fault:
            try:
                client.page_all()
            except RuntimeError as error:
                assert str(error) == "pagination cycle detected"
            else:
                raise AssertionError("a repeated cursor was not rejected")
            checks.append("cyclic cursor detected within bounded request budget")
        else:
            assert client.page_all() == list(range(7))
            assert client.request("/items?limit=999")[0] == 400
            checks += ["three pages contain seven unique IDs", "invalid page limit rejected"]
    elif scenario == "errors":
        code, body, statuses, _ = client.retry("/resource/1")
        assert statuses == ([503, 503, 503] if fault else [200])
        assert code == (503 if fault else 200)
        if fault:
            assert body == {"error": "temporarily unavailable"}
        else:
            assert client.retry("/resource/999")[2] == [404], "404 must not be retried"
            assert client.request("/records", raw=b"{")[0] == 400
            assert client.request("/control", {"mode": "healthy"})[0] == 403
        checks.append("transient failures bounded to three attempts; permanent errors not retried")
    elif scenario == "rate":
        code, _, statuses, elapsed = client.retry("/throttle?key=" + uuid.uuid4().hex)
        assert statuses == ([429, 429, 429] if fault else [429, 429, 200])
        assert code == (429 if fault else 200) and elapsed >= 1.8
        checks += ["Retry-After honored for two waits", "three-attempt retry budget enforced"]
    elif scenario == "cache":
        if fault:
            cached = json.loads(Path(cache_file).read_text(encoding="utf-8"))
            code, _, body = client.request("/resource/1", headers={"If-None-Match": cached["etag"]})
            assert code == 304 and body is None
            code, headers, fresh = client.request("/resource/1")
            assert code == 200 and headers["ETag"] == cached["etag"] and fresh != cached["body"]
            checks.append(
                "fresh unconditional read exposes a changed representation under an unchanged ETag"
            )
        else:
            code, headers, first = client.request("/resource/1")
            assert code == 200 and first["revision"] == 1
            old = headers["ETag"]
            Path(cache_file).write_text(json.dumps({"etag": old, "body": first}), encoding="utf-8")
            assert client.request("/resource/1", headers={"If-None-Match": old})[0] == 304
            control = {"X-Lab-Control": "public-training-fixture"}
            try:
                assert client.request("/revision", {"revision": 2}, control)[0] == 200
                code, headers, changed = client.request(
                    "/resource/1", headers={"If-None-Match": old}
                )
                assert code == 200 and headers["ETag"] != old and changed["revision"] == 2
            finally:
                assert client.request("/revision", {"revision": 1}, control)[0] == 200
            checks += [
                "unchanged resource returns bodyless 304",
                "changed resource invalidates old ETag",
            ]
    elif scenario == "telemetry":
        before = client.request("/metrics")[2]["requests"]
        trace = uuid.uuid4().hex
        code, headers, _ = client.request("/resource/1", headers={"X-Request-ID": trace})
        assert code == 200 and headers["X-Request-ID"] == trace
        events = client.request("/events")[2]["events"]
        matches = [event for event in events if event["trace"] == trace]
        assert len(matches) == (0 if fault else 1)
        if not fault:
            assert matches[0]["path"] == "/resource/1" and matches[0]["status"] == 200
        after = client.request("/metrics")[2]
        assert after["requests"] >= before + 3 and after["statuses"]["200"] > 0
        checks.append(
            "trace correlation "
            + (
                "loss detected despite healthy HTTP and counters"
                if fault
                else "matches the real request, response and recorded status"
            )
        )
    elif scenario == "database":
        key = uuid.uuid4().hex
        record = {"key": key, "payload": {"device": "training-router", "intent": "up"}}
        if fault:
            assert client.request("/records", record)[0] == 503
            assert client.request("/records/" + key)[0] == 404
            checks.append("SQLite query-only rejects writes without creating a partial record")
        else:
            with ThreadPoolExecutor(max_workers=8) as pool:
                codes = list(pool.map(lambda _: client.request("/records", record)[0], range(8)))
            assert codes.count(201) == 1 and codes.count(200) == 7, codes
            assert (
                client.request("/records", {"key": key, "payload": {"intent": "different"}})[0]
                == 409
            )
            assert client.request("/records/" + key)[2]["payload"] == record["payload"]
            checks += [
                "eight simultaneous submissions create exactly one record",
                "conflicting replay rejected; original payload preserved",
            ]
    else:
        raise ValueError("unknown scenario")
    return {"scenario": scenario, "phase": phase, "status": "passed", "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", nargs="?", choices=FAULTS)
    parser.add_argument("phase", nargs="?", choices=("baseline", "fault", "recovered"))
    parser.add_argument("--set-mode", choices=["healthy", *FAULTS.values()])
    parser.add_argument("--base", default="http://198.18.0.1:8080")
    parser.add_argument("--cache-file", default="/lab/cache.json")
    args = parser.parse_args()
    if args.set_mode:
        if args.scenario or args.phase:
            parser.error("--set-mode cannot be combined with an assertion scenario")
        Client(args.base).control(args.set_mode)
        print(json.dumps({"mode": args.set_mode, "status": "configured"}))
    else:
        if not args.scenario or not args.phase:
            parser.error("scenario and phase are required")
        print(
            json.dumps(run(args.base, args.scenario, args.phase, args.cache_file), sort_keys=True)
        )
