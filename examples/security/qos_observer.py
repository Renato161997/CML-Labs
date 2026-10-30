"""Read phase-specific received DSCP values from real NetFlowv5 observations."""

import argparse
import json
from pathlib import Path

from netflow_fixture import matching, snapshot


def proof(state, port, dscp):
    if not isinstance(dscp, int) or isinstance(dscp, bool) or not 0 <= dscp <= 63:
        raise ValueError("DSCP must be an integer in 0..63")
    records = matching(state, port)
    observed = sorted({r["tos"] >> 2 for r in records})
    return {
        "observed": bool(records) and observed == [dscp],
        "port": port,
        "expected_dscp": dscp,
        "received_dscp": observed,
        "matching_records": len(records),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=int, choices=(8080, 8081, 8082))
    parser.add_argument("dscp", type=int, choices=range(64))
    parser.add_argument("--state", type=Path, default=Path("/lab/netflow.json"))
    args = parser.parse_args()
    print(json.dumps(proof(snapshot(args.state), args.port, args.dscp), sort_keys=True))


if __name__ == "__main__":
    main()
