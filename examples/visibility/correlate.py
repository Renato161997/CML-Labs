"""Correlate real lab ACL and interface events; temporal pairing is not causality."""

import argparse
import json
import re
import sys
from pathlib import Path


def correlate(events, source, window=120):
    families = {"packet_denied": [], "interface_disabled": []}
    for event in events:
        if event.get("source") != source or event.get("truncated"):
            continue
        message = event["message"]
        stamp = event["received_monotonic"]
        if not isinstance(stamp, (float, int)) or not isinstance(message, str):
            raise TypeError("Invalid collector record")
        if re.search(r"IPACCESSLOG.*CML-DENY.*denied\s+icmp", message, re.IGNORECASE):
            families["packet_denied"].append(event)
        if re.search(r"%LINK-\d-.*Loopback1.*administratively down", message, re.IGNORECASE):
            families["interface_disabled"].append(event)
    pairs = [
        {"packet_denied": a, "interface_disabled": b}
        for a in families["packet_denied"]
        for b in families["interface_disabled"]
        if abs(a["received_monotonic"] - b["received_monotonic"]) <= window
    ]
    return {
        "source": source,
        "window_seconds": window,
        "event_counts": {name: len(rows) for name, rows in families.items()},
        "correlations": pairs[:4],
        "correlation_count": len(pairs),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("baseline", "single", "incident"))
    args = parser.parse_args()
    try:
        if not Path("/lab/receiver-ready").exists():
            raise RuntimeError("Collector has not bound its UDP listener")
        events = [
            json.loads(line)
            for line in Path("/lab/events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        report = correlate(events, "198.18.1.1")
        counts = report["event_counts"]
        if args.mode == "baseline" and (counts["packet_denied"] or counts["interface_disabled"]):
            raise RuntimeError("Unexpected initial event families")
        if args.mode == "single" and (
            not counts["packet_denied"]
            or counts["interface_disabled"]
            or report["correlation_count"]
        ):
            raise RuntimeError("Single-family negative control failed")
        if args.mode == "incident" and not report["correlation_count"]:
            raise RuntimeError("Both actual event families are required in the receive window")
        report.update(status="passed", mode=args.mode)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError, KeyError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
