"""Isolated UDP collector; records receive time and source without trusting headers."""

import json
import socket
import time
from datetime import UTC, datetime
from pathlib import Path


def main():
    config = json.loads(Path("/lab/syslog.json").read_text(encoding="utf-8"))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind((config["bind"], 514))
        with Path("/lab/events.jsonl").open("a", encoding="utf-8", buffering=1) as log:
            Path("/lab/receiver-ready").write_text("BOUND\n", encoding="utf-8")
            while True:
                data, sender = server.recvfrom(8193)
                log.write(
                    json.dumps(
                        {
                            "source": sender[0],
                            "received_monotonic": time.monotonic(),
                            "received_utc": datetime.now(UTC).isoformat(),
                            "truncated": len(data) > 8192,
                            "message": data.decode("utf-8", errors="replace").strip(),
                        },
                        ensure_ascii=True,
                    )
                    + "\n"
                )


if __name__ == "__main__":
    main()
