"""Finite SNMPv3 status board: measured interface state, freshness and byte rates."""

import argparse
import json
import math
import os
import re
import time
from pathlib import Path

import snmp_probe as wire

ROOT = Path("/lab")
TARGET = "198.18.0.1"
INTERFACE = "Ethernet0/1"
TABLE = ".1.3.6.1.2.1.2.2.1."


class Unavailable(ValueError):
    pass


def value_of(oid, output, kind):
    if len(output) > 2048:
        raise Unavailable("oversized_response")
    prefix = re.escape(oid) + r"\s*=\s*"
    patterns = {
        "uptime": r"Timeticks:\s*\(([0-9]+)\)[^\n]*",
        "counter": r"Counter32:\s*([0-9]+)",
        "state": r"INTEGER:\s*(?:[A-Za-z][A-Za-z_-]*\()?([1-7])\)?",
        "text": r'STRING:\s*"?([A-Za-z0-9/_-]+)"?',
    }
    match = re.fullmatch(prefix + patterns[kind] + r"\s*", output)
    if not match:
        raise Unavailable("unexpected_oid_or_type")
    value = match[1] if kind == "text" else int(match[1])
    if kind in ("counter", "uptime") and not 0 <= value <= 2**32 - 1:
        raise Unavailable("counter_out_of_range")
    return value


def collect(wrong_auth=False):
    def get(oid, kind):
        code, output = wire.request(TARGET, oid, wrong_auth=wrong_auth)
        if code:
            raise Unavailable("agent_request_failed")
        return value_of(oid, output, kind)

    uptime = get(wire.UPTIME, "uptime")
    assert get(wire.SYSNAME, "text") == "R1", "Wrong actual agent identity"
    index = None
    for candidate in range(1, 17):
        try:
            name = get(TABLE + "2." + str(candidate), "text")
        except Unavailable as exc:
            if str(exc) != "unexpected_oid_or_type":
                raise
            continue
        if name == INTERFACE:
            index = candidate
            break
    if index is None:
        raise Unavailable("declared_interface_not_found")
    sample = {
        "agent": "R1",
        "interface": INTERFACE,
        "index": index,
        "uptime_ticks": uptime,
        "state": get(TABLE + "8." + str(index), "state"),
        "rx_bytes": get(TABLE + "10." + str(index), "counter"),
        "tx_bytes": get(TABLE + "16." + str(index), "counter"),
    }
    final_uptime = get(wire.UPTIME, "uptime")
    if final_uptime < uptime:
        raise Unavailable("agent_restarted_during_collection")
    sample.update(uptime_ticks=final_uptime, monotonic=time.monotonic())
    return sample


def byte_rates(previous, current):
    if previous is None:
        return None
    if any(previous[key] != current[key] for key in ("agent", "interface", "index")):
        raise ValueError("identity_discontinuity")
    elapsed = current["monotonic"] - previous["monotonic"]
    if not math.isfinite(elapsed) or not 0 < elapsed <= 60:
        raise ValueError("stale_or_invalid_interval")
    if current["uptime_ticks"] < previous["uptime_ticks"]:
        raise ValueError("agent_uptime_discontinuity")
    result = {}
    for key in ("rx_bytes", "tx_bytes"):
        before, after = previous[key], current[key]
        if (
            type(before) is not int
            or type(after) is not int
            or not 0 <= before <= after <= 2**32 - 1
        ):
            raise ValueError("counter_discontinuity")
        rate = (after - before) / elapsed
        if not math.isfinite(rate):
            raise ValueError("invalid_rate")
        result[key + "_per_second"] = rate
    return result


def save(sample):
    cache = ROOT / "telemetry-last.json"
    assert not cache.is_symlink()
    cache.write_text(json.dumps(sample, sort_keys=True))
    cache.chmod(0o600)


def poll(wrong_auth=False, update=True):
    cache = ROOT / "telemetry-last.json"
    assert not cache.is_symlink()
    previous = json.loads(cache.read_text()) if cache.exists() else None
    try:
        sample = collect(wrong_auth)
    except Unavailable as exc:
        return {
            "available": False,
            "fresh": False,
            "reason": str(exc),
            "sample": None,
            "byte_rates": None,
            "last_known_present": previous is not None,
        }
    try:
        rates = byte_rates(previous, sample)
        reason = "first_sample" if rates is None else "measured"
    except ValueError as exc:
        rates, reason = None, str(exc)
    if update:
        save(sample)
    return {
        "available": True,
        "fresh": True,
        "sample": sample,
        "byte_rates": rates,
        "rate_status": reason,
    }


def wrong_auth():
    value = (ROOT / "telemetry-auth-mode").read_text().strip()
    assert value in ("good", "wrong"), "Unknown fixture authentication mode"
    return value == "wrong"


def report(phase):
    wrong = wrong_auth()
    value = poll(wrong, update=False)
    if phase == "unavailable":
        assert (
            wrong
            and value["available"] is False
            and value["sample"] is None
            and value["byte_rates"] is None
        )
    else:
        assert not wrong and value["available"] is True and value["fresh"] is True
        assert value["sample"]["state"] == (2 if phase == "down" else 1)
        if phase == "rates":
            assert value["byte_rates"] is not None
            assert all(rate > 0 for rate in value["byte_rates"].values())
        save(value["sample"])
    return {"status": "passed", "phase": phase, **value}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "configure",
            "healthy",
            "down",
            "rates",
            "unavailable",
            "bad-auth",
            "good-auth",
            "watch",
        ),
    )
    args = parser.parse_args()
    assert (
        os.geteuid() == 0
        and (ROOT / "CML-TELEMETRY-BOARD").read_text().strip() == "CML-TELEMETRY-V1"
    )
    if args.action in ("configure", "bad-auth", "good-auth"):
        path = ROOT / "telemetry-auth-mode"
        assert not path.is_symlink()
        path.write_text("wrong" if args.action == "bad-auth" else "good")
        path.chmod(0o600)
        value = {"status": "passed", "wrong_auth": args.action == "bad-auth"}
    elif args.action == "watch":
        while True:
            value = poll(wrong_auth())
            if not value["available"]:
                print("UNAVAILABLE | no fresh interface state or byte rate", flush=True)
            else:
                sample = value["sample"]
                print(
                    f"{sample['interface']} | state={sample['state']} | RX={sample['rx_bytes']} bytes | TX={sample['tx_bytes']} bytes | rates={value['byte_rates']} | {value['rate_status']}",
                    flush=True,
                )
            time.sleep(2)
    else:
        value = report(args.action)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
