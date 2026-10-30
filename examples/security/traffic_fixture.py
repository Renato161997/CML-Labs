"""Plain HTTP packet/peer fixture restricted to isolated benchmark or loopback IPs."""

from __future__ import annotations

import argparse
import http.client
import http.server
import ipaddress
import json


def fixture_address(value):
    address = ipaddress.IPv4Address(value)
    if not (address in ipaddress.IPv4Network("198.18.0.0/15") or address.is_loopback):
        raise ValueError("Only benchmark/loopback fixture IPv4 targets are accepted")
    return str(address)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        data = json.dumps(
            {"server": self.server.fixture_label, "peer": self.client_address[0]},
            sort_keys=True,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def server(address, port, label):
    value = http.server.ThreadingHTTPServer((fixture_address(address), port), Handler)
    value.fixture_label = label
    value.daemon_threads = True
    return value


def probe(address, port=8080, timeout=3):
    address = fixture_address(address)
    connection = http.client.HTTPConnection(address, port, timeout=timeout)
    try:
        connection.request("GET", "/health")
        response = connection.getresponse()
        body = response.read(4097)
        if len(body) > 4096:
            raise ValueError("Oversized fixture response")
        value = json.loads(body)
        if set(value) != {"peer", "server"}:
            raise ValueError("Unexpected fixture schema")
        return {"reachable": True, "status": response.status, **value}
    except TimeoutError:
        return {"reachable": False, "reason": "timeout"}
    except ConnectionRefusedError:
        return {"reachable": False, "reason": "connection_refused"}
    except OSError:
        return {"reachable": False, "reason": "network_rejected"}
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("serve", "probe"))
    parser.add_argument("address", type=fixture_address)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--label", choices=("INSIDE", "OUTSIDE"), default="OUTSIDE")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged fixture port")
    if args.action == "serve":
        with server(args.address, args.port, args.label) as listener:
            listener.serve_forever(poll_interval=0.1)
    else:
        print(json.dumps(probe(args.address, args.port), sort_keys=True))


if __name__ == "__main__":
    main()
