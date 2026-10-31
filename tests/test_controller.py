import http.client
import importlib.util
import os
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "examples/automation"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SOURCE / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


contract = load("controller_contract")
with patch.dict(sys.modules, {"controller_contract": contract}):
    controller = load("controller")
    client = load("controller_client")


class Device:
    def __init__(self, state):
        self.state = state
        self.facts = {"hostname": "API", "ipv4": "198.18.0.1", "mask": "255.255.255.252"}

    def __enter__(self):
        if self.state.get("unavailable"):
            raise OSError("Unit-test backend unavailable")
        return self

    def __exit__(self, *error):
        pass

    def hops(self):
        return list(self.state["hops"])

    def set(self, hops):
        if self.state.get("reject_restore") and hops == [contract.GOOD]:
            raise OSError("Unit-test compensation unavailable")
        self.state["writes"].append(list(hops))
        self.state["hops"] = list(hops)


class DeviceController(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.state = {"hops": [], "writes": []}
        self.app = self.new_app()

    def new_app(self, **options):
        return controller.Controller(
            self.root / "jobs.sqlite3", contract.approvals, lambda: Device(self.state), **options
        )

    @contextmanager
    def serving(self):
        with controller.make_server(("127.0.0.1", 0), self.app) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with (
                    patch.object(client, "HOST", "127.0.0.1"),
                    patch.object(client, "PORT", server.server_port),
                    patch.object(client, "ROOT", self.root),
                ):
                    yield server.server_port
            finally:
                server.shutdown()
                thread.join(5)
                self.assertFalse(thread.is_alive())

    def test_intent_scope_types_and_injection_are_rejected_before_mutation(self):
        good = contract.intent("install-1")
        for changes in [
            {"device": "OTHER"},
            {"prefix": "0.0.0.0/0"},
            {"next_hop": "198.18.0.3\nshutdown"},
            {"state": True},
            {"request_id": "../../root"},
            {"request_id": 12},
            {"approved": True},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.app.apply({**good, **changes})
        self.assertEqual(self.state["writes"], [])
        self.assertEqual(self.app.history(), {"jobs": [], "events": []})

    def test_unapproved_intent_cannot_create_a_job_or_write(self):
        with self.assertRaises(controller.Problem) as error:
            self.app.apply(contract.intent("unapproved-1"))
        self.assertEqual(error.exception.status, 403)
        self.assertEqual(self.app.history()["jobs"], [])
        self.assertEqual(self.state["writes"], [])

    def test_durable_success_replays_without_a_second_write_or_event(self):
        result = self.app.apply(contract.intent("install-1"))
        self.assertTrue(result["applied_now"])
        before = self.app.history()
        reloaded = self.new_app()
        result = reloaded.apply(contract.intent("install-1"))
        self.assertTrue(result["replayed"])
        self.assertFalse(result["applied_now"])
        self.assertEqual(reloaded.history(), before)
        self.assertEqual(self.state["writes"], [[contract.GOOD]])

    def test_request_id_conflict_is_not_a_new_approval_or_device_write(self):
        self.app.apply(contract.intent("install-1"))
        before = self.app.history()
        with self.assertRaises(controller.Problem) as error:
            self.app.apply(contract.intent("install-1", "absent"))
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.app.history(), before)
        self.assertEqual(self.state["writes"], [[contract.GOOD]])

    def test_concurrent_duplicates_have_one_operation_and_one_replay(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            values = list(
                pool.map(lambda _: self.app.apply(contract.intent("install-1")), range(2))
            )
        self.assertEqual(sum(value["applied_now"] for value in values), 1)
        self.assertEqual(sum(value["replayed"] for value in values), 1)
        self.assertEqual(self.state["writes"], [[contract.GOOD]])
        self.assertEqual(self.app.history()["jobs"][0]["attempts"], 1)

    def test_confirmation_fault_restores_actual_before_state_and_allows_retry(self):
        self.app.apply(contract.intent("install-1"))
        self.app.fault = lambda: True
        with self.assertRaises(controller.Problem) as error:
            self.app.apply(contract.intent("rollback-1", "absent"))
        self.assertEqual(error.exception.status, 502)
        self.assertTrue(error.exception.job["rollback_verified"])
        self.assertEqual(error.exception.job["status"], "failed")
        self.assertEqual(self.state["hops"], [contract.GOOD])
        self.assertEqual(self.state["writes"], [[contract.GOOD], [], [contract.GOOD]])
        self.app.fault = lambda: False
        result = self.app.apply(contract.intent("rollback-1", "absent"))
        self.assertEqual(result["job"]["attempts"], 2)
        self.assertEqual(result["job"]["status"], "succeeded")
        self.assertEqual(self.state["hops"], [])

    def test_failed_compensation_is_never_reported_as_verified_rollback(self):
        self.app.apply(contract.intent("install-1"))
        self.app.fault = lambda: True
        self.state["reject_restore"] = True
        with self.assertRaises(controller.Problem) as error:
            self.app.apply(contract.intent("rollback-1", "absent"))
        self.assertFalse(error.exception.job["rollback_verified"])
        self.assertEqual(error.exception.job["status"], "failed")
        self.assertEqual(self.state["hops"], [])
        self.assertTrue(self.app.observed()["drift"])

    def test_pending_job_after_process_interruption_reconciles_actual_state(self):
        def interrupted():
            raise KeyboardInterrupt()

        self.app.fault = interrupted
        with self.assertRaises(KeyboardInterrupt):
            self.app.apply(contract.intent("install-1"))
        self.assertEqual(self.app.history()["jobs"][0]["status"], "pending")
        self.assertEqual(self.state["hops"], [contract.GOOD])
        reloaded = self.new_app()
        result = reloaded.apply(contract.intent("install-1"))
        self.assertFalse(result["applied_now"])
        self.assertEqual(result["job"]["attempts"], 2)
        self.assertEqual(result["job"]["status"], "succeeded")
        self.assertEqual(self.state["writes"], [[contract.GOOD]])

    def test_assurance_uses_observed_route_not_the_last_successful_job(self):
        self.app.apply(contract.intent("install-1"))
        self.state["hops"] = [contract.BAD]
        value = self.app.observed()
        self.assertEqual(value["configured_next_hops"], [contract.BAD])
        self.assertEqual(value["desired_next_hops"], [contract.GOOD])
        self.assertEqual(value["off_link_next_hops"], [contract.BAD])
        self.assertTrue(value["drift"])

    def test_backend_failure_has_no_stale_before_state_on_retry(self):
        self.state["unavailable"] = True
        with self.assertRaises(controller.Problem) as error:
            self.app.apply(contract.intent("install-1"))
        self.assertIsNone(error.exception.job["before_hops"])
        self.assertIsNone(error.exception.job["rollback_verified"])
        self.state["unavailable"] = False
        self.assertTrue(self.app.apply(contract.intent("install-1"))["applied_now"])

    def test_real_http_client_contract_and_model_rejections(self):
        with self.serving():
            self.assertEqual(client.run("baseline")["status"], "passed")
        self.assertEqual(self.state["writes"], [[contract.GOOD]])

    def test_http_backend_unavailability_is_not_empty_success(self):
        self.state["unavailable"] = True
        with self.serving():
            self.assertEqual(client.request("GET", "/health")[0], 200)
            status, value = client.request("GET", "/v1/device")
            self.assertEqual(status, 503)
            self.assertEqual(value["error"], "backend_unavailable")
            self.assertNotIn("facts", value)
            self.assertEqual(client.request("GET", "/not-a-resource")[0], 404)

    def test_http_rejects_duplicate_fields_body_limits_and_unexpected_types(self):
        with self.serving() as port:
            for body, headers, expected in [
                (b'{"request_id":"install-1","request_id":"withdraw-1"}', {}, 422),
                (b"{}", {"Content-Type": "text/plain"}, 415),
                (b"x" * 4097, {}, 413),
                (b"{}", {"Transfer-Encoding": "chunked"}, 400),
                (b"{}", {"Authorization": "Bearer \u00fc"}, 401),
            ]:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                try:
                    connection.request(
                        "POST",
                        "/v1/route-intents",
                        body,
                        {
                            "Authorization": "Bearer " + contract.TOKEN,
                            "Content-Type": "application/json",
                            **headers,
                        },
                    )
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    response.read()
                finally:
                    connection.close()
        self.assertEqual(self.app.history()["jobs"], [])
        self.assertEqual(self.state["writes"], [])

    def test_foreign_or_unsafe_process_can_never_be_signalled(self):
        (self.root / "controller.pid").write_text("451")
        proc = self.root / "proc/451"
        proc.mkdir(parents=True)
        (proc / "cmdline").write_bytes(b"/usr/bin/python3\0/unrelated.py\0serve\0")
        with (
            patch.object(controller, "ROOT", self.root),
            patch.object(controller, "PROC", self.root / "proc"),
            patch.object(os, "kill") as signal,
        ):
            controller.stop()
            signal.assert_not_called()
        with self.assertRaises(ValueError):
            controller.owned(1)
