import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from test_api_core import load_example, service

frontend = load_example("frontend")
probe = load_example("distribution_probe")


class DistributionIntegrationTests(unittest.TestCase):
    def test_scale_in_real_backend_failures_and_recovery(self):
        active = []

        def start(handler, port=0):
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            active.append((server, worker))
            return server

        def stop(server):
            pair = next(pair for pair in active if pair[0] is server)
            server.shutdown()
            server.server_close()
            pair[1].join(timeout=5)
            active.remove(pair)

        with tempfile.TemporaryDirectory() as directory:
            states = [service.State(Path(directory) / (str(i) + ".sqlite")) for i in range(2)]
            try:
                apps = [start(service.handler_for(state)) for state in states]
                pairs = sorted(
                    zip(apps, states), key=lambda pair: pair[0].server_port, reverse=True
                )
                apps = [pair[0] for pair in pairs]
                states = [pair[1] for pair in pairs]
                ports = [app.server_port for app in apps]
                upstreams = tuple("http://127.0.0.1:" + str(port) for port in ports)
                gateway = start(frontend.handler_for(upstreams))
                base = "http://127.0.0.1:" + str(gateway.server_port)
                with patch.object(probe, "BASE", base), patch.object(probe, "UPSTREAMS", upstreams):
                    self.assertEqual(probe.run("baseline", True)["status"], "passed")
                    self.assertEqual(probe.request("/pool", {"upstreams": []})[0], 400)
                    self.assertEqual(
                        probe.request("/pool", {"upstreams": ["http://invalid.example"]})[0], 400
                    )
                    self.assertEqual(probe.request("/pool", {"upstreams": [upstreams[0]]})[0], 200)
                    self.assertEqual(probe.run("scale-in", True)["status"], "passed")
                    probe.request("/pool", {"upstreams": list(upstreams)})
                    stop(apps[0])
                    self.assertEqual(probe.run("first-down")["status"], "passed")
                    stop(apps[1])
                    self.assertEqual(probe.run("all-down")["status"], "passed")
                    start(service.handler_for(states[0]), ports[0])
                    self.assertEqual(probe.run("first-only")["status"], "passed")
                    start(service.handler_for(states[1]), ports[1])
                    self.assertEqual(probe.run("recovered", True)["status"], "passed")
            finally:
                while active:
                    stop(active[-1][0])
