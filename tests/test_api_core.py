import importlib.util
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[1] / "examples/api-core"


def load_example(name):
    spec = importlib.util.spec_from_file_location("api_core_" + name, EXAMPLES / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


service, client = load_example("service"), load_example("client")


class ApiProtocolIntegrationTests(unittest.TestCase):
    def test_real_http_faults_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            state = service.State(Path(directory) / "events.sqlite")
            http = ThreadingHTTPServer(("127.0.0.1", 0), service.handler_for(state))
            worker = threading.Thread(target=http.serve_forever, daemon=True)
            worker.start()
            base = "http://127.0.0.1:" + str(http.server_port)
            try:
                for scenario, fault in client.FAULTS.items():
                    with self.subTest(scenario=scenario):
                        probe = client.Client(base)
                        probe.control("healthy")
                        cache = Path(directory) / "cache.json"
                        self.assertEqual(
                            client.run(base, scenario, "baseline", cache)["status"], "passed"
                        )
                        probe.control(fault)
                        self.assertEqual(
                            client.run(base, scenario, "fault", cache)["status"], "passed"
                        )
                        probe.control("healthy")
                        self.assertEqual(
                            client.run(base, scenario, "recovered", cache)["status"], "passed"
                        )
            finally:
                http.shutdown()
                http.server_close()
                worker.join(timeout=5)
