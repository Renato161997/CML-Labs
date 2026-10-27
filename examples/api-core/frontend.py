"""Small inspectable stateless HTTP failover frontend for isolated CML labs."""

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

UPSTREAMS = ("http://198.18.1.2:8080", "http://198.18.1.3:8080")


def handler_for(upstreams=UPSTREAMS):
    lock = threading.Lock()
    pool = list(upstreams)
    sequence = 0

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            nonlocal sequence
            if self.path == "/health":
                return self.reply(200, {"service": "frontend"})
            if self.path != "/resource/1":
                return self.reply(404, {"error": "not found"})
            with lock:
                index = sequence % len(pool)
                sequence += 1
                ordered = pool[index:] + pool[:index]
            for attempt, upstream in enumerate(ordered, 1):
                try:
                    request = Request(upstream + self.path)
                    with build_opener(ProxyHandler({})).open(request, timeout=0.6) as response:
                        body = json.load(response)
                        return self.reply(
                            response.code, {"backend": upstream, "attempts": attempt, "data": body}
                        )
                except (HTTPError, URLError, TimeoutError, ConnectionError):
                    continue
            return self.reply(503, {"error": "no healthy backend", "attempts": len(ordered)})

        def do_POST(self):
            nonlocal pool
            if (
                self.path != "/pool"
                or self.headers.get("X-Lab-Control") != "public-training-fixture"
            ):
                return self.reply(403, {"error": "denied"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length < 1024:
                    raise ValueError
                selected = json.loads(self.rfile.read(length))["upstreams"]
                if (
                    not isinstance(selected, list)
                    or not selected
                    or len(set(selected)) != len(selected)
                    or any(value not in upstreams for value in selected)
                ):
                    raise ValueError
            except (ValueError, TypeError, KeyError):
                return self.reply(400, {"error": "invalid pool"})
            with lock:
                pool = selected
            return self.reply(200, {"upstreams": selected})

    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="198.18.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    ThreadingHTTPServer((args.bind, args.port), handler_for()).serve_forever()
