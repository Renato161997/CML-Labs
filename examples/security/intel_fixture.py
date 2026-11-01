"""Closed synthetic indicator profile with real HTTP ETag/cache/uncertainty probes."""

import argparse
import hashlib
import http.client
import http.server
import ipaddress
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-INDICATOR-FEED-V1"
SOURCE, ANALYST = "198.18.0.1", "198.18.0.2"
TARGET = "198.18.10.10"


def stamp(epoch):
    return (
        datetime.fromtimestamp(epoch, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", value
    ):
        raise ValueError("Timestamp outside the closed millisecond UTC profile")
    return datetime.fromisoformat(value).timestamp()


def identifier(kind, index):
    return kind + "--" + str(uuid.UUID(int=0x123456789ABCDEF00000000000000000 + index, version=4))


def valid_id(value, kind):
    if not isinstance(value, str) or not value.startswith(kind + "--"):
        raise ValueError("Unexpected object ID")
    parsed = uuid.UUID(value[len(kind) + 2 :])
    if parsed.version != 4 or str(parsed) != value[len(kind) + 2 :]:
        raise ValueError("Object ID outside the declared v4 UUID profile")


def bundle(anchor, withdrawn=False):
    objects = []
    for index in range(5):
        value = {
            "type": "indicator",
            "spec_version": "2.1",
            "id": identifier("indicator", index + 1),
            "created": stamp(anchor - 7200),
            "modified": stamp(anchor + (1 if index == 0 and withdrawn else 0)),
            "name": "Synthetic lab indicator " + str(index),
            "pattern": "[ipv4-addr:value = '198.18.10." + str(10 + index) + "']",
            "pattern_type": "stix",
            "pattern_version": "2.1",
            "valid_from": stamp(anchor - 3600),
            "valid_until": stamp(anchor + 3600),
            "confidence": 85,
            "revoked": False,
        }
        if index == 1:
            value["confidence"] = 35
        if index == 2:
            value["valid_from"] = stamp(anchor - 7200)
            value["valid_until"] = stamp(anchor - 60)
        if index == 3 or (index == 0 and withdrawn):
            value["revoked"] = True
        if index == 4:
            value["valid_from"] = stamp(anchor + 3600)
            value["valid_until"] = stamp(anchor + 7200)
        objects.append(value)
    return {"type": "bundle", "id": identifier("bundle", 0), "objects": objects}


def unique(pairs):
    value = {}
    for k, v in pairs:
        if k in value:
            raise ValueError("Duplicate JSON field")
        value[k] = v
    return value


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def tag(raw):
    return '"' + hashlib.sha256(raw).hexdigest() + '"'


def parsed(raw):
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= 65536:
        raise ValueError("Feed size outside the bounded profile")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    if (
        not isinstance(value, dict)
        or set(value) != {"type", "id", "objects"}
        or value["type"] != "bundle"
        or not isinstance(value["objects"], list)
        or not 1 <= len(value["objects"]) <= 32
    ):
        raise ValueError("Feed is not the closed bundle profile")
    valid_id(value["id"], "bundle")
    required = {
        "type",
        "spec_version",
        "id",
        "created",
        "modified",
        "pattern",
        "pattern_type",
        "valid_from",
    }
    optional = {"pattern_version", "valid_until", "revoked", "confidence", "name"}
    result = []
    seen = set()
    for item in value["objects"]:
        if not isinstance(item, dict) or not required <= set(item) <= required | optional:
            raise ValueError("Indicator fields outside the bounded profile")
        if (
            item["type"],
            item["spec_version"],
            item["pattern_type"],
            item.get("pattern_version", "2.1"),
        ) != ("indicator", "2.1", "stix", "2.1"):
            raise ValueError("Unsupported indicator or pattern version")
        valid_id(item["id"], "indicator")
        if item["id"] in seen:
            raise ValueError("Multiple object versions are outside this exercise")
        seen.add(item["id"])
        if timestamp(item["modified"]) < timestamp(item["created"]):
            raise ValueError("Invalid version timestamps")
        start = timestamp(item["valid_from"])
        end = timestamp(item["valid_until"]) if "valid_until" in item else None
        if end is not None and end <= start:
            raise ValueError("Invalid indicator validity interval")
        confidence = item.get("confidence")
        if "confidence" in item and (type(confidence) is not int or not 0 <= confidence <= 100):
            raise ValueError("Invalid producer confidence")
        if "name" in item and (
            not isinstance(item["name"], str) or not 1 <= len(item["name"]) <= 128
        ):
            raise ValueError("Invalid bounded indicator name")
        revoked = item.get("revoked", False)
        if type(revoked) is not bool:
            raise ValueError("Invalid revocation scalar")
        if not isinstance(item["pattern"], str):
            raise TypeError("Invalid pattern scalar")
        match = re.fullmatch(r"\[ipv4-addr:value = '([0-9.]+)'\]", item["pattern"])
        if not match:
            raise ValueError("Only the declared literal IPv4 pattern is supported")
        address = ipaddress.IPv4Address(match[1])
        if address not in ipaddress.IPv4Network("198.18.0.0/15"):
            raise ValueError("Only synthetic benchmark indicators are accepted")
        result.append(
            {
                "id": item["id"],
                "address": str(address),
                "from": start,
                "until": end,
                "revoked": revoked,
                "confidence": confidence,
            }
        )
    return result


def matches(records, address, now):
    return [
        r["id"]
        for r in records
        if r["address"] == address
        and not r["revoked"]
        and r["from"] <= now
        and (r["until"] is None or now < r["until"])
        and r["confidence"] is not None
        and r["confidence"] >= 70
    ]


def cache_load(path):
    if not path.exists():
        return None, False
    try:
        if path.is_symlink():
            raise ValueError("Cache link refused")
        value = json.loads(path.read_text(), object_pairs_hook=unique)
        if set(value) != {"etag", "body"} or not isinstance(value["body"], str):
            raise ValueError("Invalid cache envelope")
        raw = value["body"].encode("utf-8")
        if value["etag"] != tag(raw):
            raise ValueError("Cache body does not match its source ETag")
        parsed(raw)
        return value, False
    except (ValueError, TypeError, KeyError, UnicodeError):
        return None, True


def fetch(path):
    cached, corrupt = cache_load(path)
    headers = {} if cached is None else {"If-None-Match": cached["etag"]}
    conn = http.client.HTTPConnection(SOURCE, 8080, timeout=3)
    try:
        conn.request("GET", "/feed", headers=headers)
        response = conn.getresponse()
        raw = response.read(65537)
        status = response.status
        etag = response.getheader("ETag")
        if status == 304:
            if cached is None or raw or etag != cached["etag"]:
                raise ValueError("Unusable conditional response")
            records = parsed(cached["body"].encode("utf-8"))
        elif status == 200:
            if response.getheader("Content-Type") != "application/json" or etag != tag(raw):
                raise ValueError("Unverified representation")
            records = parsed(raw)
            value = {"etag": etag, "body": raw.decode("utf-8")}
            temp = path.with_suffix(".next")
            with temp.open("x") as output:
                json.dump(value, output, sort_keys=True)
            temp.chmod(0o600)
            temp.replace(path)
        else:
            raise ValueError("Source unavailable")
        return {
            "verified": True,
            "wire_status": status,
            "records": records,
            "cache_corruption_detected": corrupt,
        }
    except (OSError, ValueError, TypeError, http.client.HTTPException):
        return {
            "verified": False,
            "wire_status": locals().get("status"),
            "records": [],
            "cache_corruption_detected": corrupt,
        }
    finally:
        conn.close()


def make_server(address):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/feed":
                self.send_error(404)
                return
            mode = (ROOT / "intel-mode").read_text().strip()
            assert mode in ("healthy", "unavailable", "malformed", "withdrawn")
            if mode == "unavailable":
                self.send_response(503)
                self.end_headers()
                return
            anchor = float((ROOT / "intel-anchor").read_text())
            value = bundle(anchor, mode == "withdrawn")
            if mode == "malformed":
                value["objects"][0]["confidence"] = 101
            raw = encoded(value)
            etag = tag(raw)
            if self.headers.get("If-None-Match") == etag:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("ETag", etag)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    return http.server.HTTPServer(address, Handler)


def serve():
    make_server((SOURCE, 8080)).serve_forever()


def configure(role):
    address = SOURCE if role == "SOURCE" else ANALYST
    subprocess.run(
        ["ip", "addr", "add", address + "/30", "dev", "eth1"], check=True, capture_output=True
    )
    subprocess.run(["ip", "link", "set", "eth1", "up"], check=True, capture_output=True)
    if role == "SOURCE":
        (ROOT / "intel-mode").write_text("healthy")
        (ROOT / "intel-anchor").write_text(str(int(time.time())))
        with (ROOT / "intel-server.log").open("ab") as output:
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "serve"],
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    return {"status": "passed", "configured": role}


def probe(phase):
    path = ROOT / "intel-cache.json"
    if phase == "corrupt-cache":
        cached, _ = cache_load(path)
        assert cached is not None
        cached["body"] += " "
        path.write_text(json.dumps(cached))
        phase = "healed-cache"
    value = fetch(path)
    if phase in ("offline", "invalid-feed"):
        assert value["verified"] is False and value["records"] == []
        expected = 503 if phase == "offline" else 200
        assert value["wire_status"] == expected
        return {
            "status": "passed",
            "phase": phase,
            "verdict": "unknown",
            "verified": False,
            "wire_status": expected,
            "unavailable_is_not_benign": True,
        }
    assert value["verified"] is True
    records = value["records"]
    now = time.time()
    found = matches(records, TARGET, now)
    assert len(records) == 5 and {r["address"] for r in records} == {
        "198.18.10." + str(i) for i in range(10, 15)
    }
    for suffix in range(11, 15):
        assert matches(records, "198.18.10." + str(suffix), now) == []
    if phase in ("baseline", "cached", "recovered"):
        assert len(found) == 1
    else:
        assert phase in ("withdrawn", "healed-cache", "cached-withdrawn") and found == []
    if phase in ("cached", "cached-withdrawn"):
        assert value["wire_status"] == 304
    if phase in ("baseline", "withdrawn", "healed-cache"):
        assert value["wire_status"] == 200
    if phase == "healed-cache":
        assert value["cache_corruption_detected"] is True
    return {
        "status": "passed",
        "phase": phase,
        "verified": True,
        "wire_status": value["wire_status"],
        "matching_indicators": len(found),
        "verdict": "matched" if found else "no-match-not-benign",
        "inactive_indicators_excluded": True,
        "cache_corruption_detected": value["cache_corruption_detected"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "configure",
            "serve",
            "baseline",
            "cached",
            "cached-withdrawn",
            "offline",
            "invalid-feed",
            "recovered",
            "withdrawn",
            "corrupt-cache",
            "healthy",
            "unavailable",
            "malformed",
            "withdraw",
        ],
    )
    action = parser.parse_args().action
    if os.geteuid() != 0 or (ROOT / "CML-INTEL-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the synthetic marked indicator fixture is accepted")
    role = (ROOT / "intel-role").read_text().strip()
    assert role in ("SOURCE", "ANALYST")
    if action == "configure":
        value = configure(role)
    elif action == "serve":
        assert role == "SOURCE"
        serve()
        return
    elif action in ("healthy", "unavailable", "malformed", "withdraw"):
        assert role == "SOURCE"
        mode = "withdrawn" if action == "withdraw" else action
        (ROOT / "intel-mode").write_text(mode)
        value = {"status": "passed", "source_mode": mode}
    else:
        assert role == "ANALYST"
        value = probe(action)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
