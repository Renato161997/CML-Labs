import copy
import importlib.util
import re
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import yaml
from embed_webhook import update as update_embedded
from labtools import (
    UniqueLoader,
    check_evidence,
    config_signature,
    graph_signature,
    load,
    require_resource_budget,
    validate,
)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


receiver = module("receiver", ROOT / "examples/webhook/receiver.py")
probe = module("probe", ROOT / "examples/webhook/probe.py")


class TopologyQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = load(next((ROOT / "labs").rglob("017-single-area-ospfv2.yaml")))

    def test_all_topologies(self):
        for path in (ROOT / "labs").rglob("*.yaml"):
            with self.subTest(path=path):
                self.assertEqual(validate(load(path)), [])

    def test_catalyst_q200_requires_complete_port_mapping_and_full_memory(self):
        topology = copy.deepcopy(self.sample)
        node = topology["nodes"][0]
        node["node_definition"] = "cat9000v-q200"
        labels = ["GigabitEthernet0/0", *[f"GigabitEthernet1/0/{i}" for i in range(1, 9)]]
        node["interfaces"] = [{"id": "i0", "label": "Loopback0", "type": "loopback"}] + [
            {"id": f"i{i + 1}", "label": label, "type": "physical", "slot": i}
            for i, label in enumerate(labels)
        ]
        node["ram"] = 12288
        self.assertEqual(validate(topology), [])
        node["node_definition"] = "cat9000v-uadp"
        node["ram"] = 18432
        self.assertEqual(validate(topology), [])
        node["ram"] = 12288
        self.assertTrue(any("18432 MiB" in error for error in validate(topology)))
        node["node_definition"] = "cat9000v-q200"
        node["interfaces"].pop()
        self.assertTrue(any("first eight data slots" in error for error in validate(topology)))
        node["ram"] = 4096
        self.assertTrue(any("12288 MiB" in error for error in validate(topology)))

    def test_large_case_requires_single_selection_and_real_free_memory(self):
        with self.assertRaises(ValueError):
            require_resource_budget(14336, 4096, 1)
        with self.assertRaises(ValueError):
            require_resource_budget(14336, 16384, 2, 64 * 1024**3)
        for unknown_or_low in (None, 31 * 1024**3):
            with self.assertRaises(ValueError):
                require_resource_budget(14336, 16384, 1, unknown_or_low)
        require_resource_budget(14336, 16384, 1, 32 * 1024**3)
        require_resource_budget(20480, 24576, 1, 48 * 1024**3)
        require_resource_budget(4096, 4096, 3)
        for invalid in (True, 0, 32769, 8192.0):
            with self.assertRaises(ValueError):
                require_resource_budget(1024, invalid, 1, 64 * 1024**3)

    def test_relative_documentation_links_exist(self):
        for path in ROOT.rglob("*.md"):
            if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
                continue
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                with self.subTest(document=path, target=target):
                    self.assertTrue((path.parent / unquote(parsed.path)).exists())

    def test_dangling_node_is_rejected(self):
        d = copy.deepcopy(self.sample)
        d["links"][0]["n1"] = "missing"
        self.assertTrue(validate(d))

    def test_cml_title_length_limit_is_checked(self):
        d = copy.deepcopy(self.sample)
        d["lab"]["title"] = "x" * 65
        self.assertTrue(validate(d))

    def test_integer_interface_is_rejected(self):
        d = copy.deepcopy(self.sample)
        d["links"][0]["i1"] = 0
        self.assertTrue(validate(d))

    def test_native_radio_models_use_reference_ports_and_ram(self):
        from labtools import RAM_MIB

        data = copy.deepcopy(self.sample)
        data["links"] = []
        for node, kind in zip(data["nodes"], ("wireless-ap", "wireless-client"), strict=True):
            node["node_definition"] = kind
            node["interfaces"] = [{"id": "i0", "label": "ens2", "type": "physical", "slot": 0}]
            node["configuration"] = [{"name": "user-data", "content": "#cloud-config\n"}]
        self.assertEqual(validate(data), [])
        self.assertEqual(sum(RAM_MIB[n["node_definition"]] for n in data["nodes"]), 4096)
        data["nodes"][0]["interfaces"][0]["label"] = "eth0"
        self.assertTrue(any("label does not match slot" in error for error in validate(data)))

    def test_wireless_seed_cannot_claim_ignored_metadata_or_reordered_files(self):
        data = copy.deepcopy(self.sample)
        data["links"] = []
        node = data["nodes"][0]
        node["node_definition"] = "wireless-ap"
        node["interfaces"] = [{"id": "i0", "label": "ens2", "type": "physical", "slot": 0}]
        user = {"name": "user-data", "content": "#cloud-config\n"}
        network = {"name": "network-config", "content": "version: 2\n"}
        for files in [
            [{"name": "meta-data", "content": "ignored"}, user],
            [network, user],
            [user, user],
        ]:
            node["configuration"] = files
            self.assertTrue(any("editable user-data" in error for error in validate(data)))
        node["configuration"] = [user, network]
        self.assertEqual(validate(data), [])

    def test_reused_interface_is_rejected(self):
        d = copy.deepcopy(self.sample)
        d["links"].append(dict(d["links"][0], id="extra"))
        self.assertTrue(validate(d))

    def test_loopback_link_is_rejected(self):
        d = copy.deepcopy(self.sample)
        d["links"][0]["i1"] = "i0"
        self.assertTrue(validate(d))

    def test_duplicate_node_id_is_rejected(self):
        d = copy.deepcopy(self.sample)
        d["nodes"][1]["id"] = d["nodes"][0]["id"]
        self.assertTrue(validate(d))

    def test_external_connector_is_rejected(self):
        d = copy.deepcopy(self.sample)
        d["nodes"][0]["node_definition"] = "external_connector"
        self.assertTrue(validate(d))

    def test_wrong_interface_slot_label_is_rejected(self):
        d = copy.deepcopy(self.sample)
        d["nodes"][0]["interfaces"][1]["label"] = "GigabitEthernet9/9"
        self.assertTrue(validate(d))

    def test_duplicate_yaml_key_is_rejected(self):
        with self.assertRaises(ValueError):
            yaml.load("lab: one\nlab: two\n", Loader=UniqueLoader)

    def test_import_normalization_allows_only_terminal_newlines(self):
        d = copy.deepcopy(self.sample)
        d["nodes"][0]["configuration"][0]["content"] = d["nodes"][0]["configuration"][0][
            "content"
        ].rstrip("\n")
        self.assertEqual(config_signature(d["nodes"]), config_signature(self.sample["nodes"]))
        d["nodes"][0]["configuration"][0]["content"] += "\ninterface Loopback99\n"
        self.assertNotEqual(config_signature(d["nodes"]), config_signature(self.sample["nodes"]))

    def test_graph_comparison_detects_a_rewired_port(self):
        d = copy.deepcopy(self.sample)
        d["links"][0]["i1"] = "i2"
        self.assertNotEqual(graph_signature(d), graph_signature(self.sample))

    def test_graph_comparison_ignores_export_id_relabeling(self):
        d = copy.deepcopy(self.sample)
        old = d["nodes"][0]["id"]
        d["nodes"][0]["id"] = "new-id"
        for link in d["links"]:
            for side in ("1", "2"):
                if link["n" + side] == old:
                    link["n" + side] = "new-id"
        self.assertEqual(graph_signature(d), graph_signature(self.sample))

    def test_embedded_offline_sources_match_repository(self):
        self.assertEqual(update_embedded(check=True), [])

    def test_stale_live_evidence_is_rejected(self):
        self.assertTrue(check_evidence({"sha256": "old"}, "lab.yaml", "current", "import"))

    def test_failed_check_cannot_claim_functional_pass(self):
        proof = {
            "sha256": "current",
            "status": "passed",
            "cml_version": "2.10.1",
            "test_lab_removed": True,
            "checks": [{"passed": False}],
        }
        self.assertTrue(check_evidence(proof, "lab.yaml", "current", "runtime"))

    def test_missing_cleanup_cannot_claim_functional_pass(self):
        proof = {
            "sha256": "current",
            "status": "passed",
            "cml_version": "2.10.1",
            "checks": [{"passed": True}],
        }
        self.assertTrue(check_evidence(proof, "lab.yaml", "current", "runtime"))

    def test_changed_acceptance_plan_invalidates_a_pass(self):
        proof = {
            "sha256": "current",
            "status": "passed",
            "cml_version": "2.10.1",
            "test_lab_removed": True,
            "checks": [{"passed": True}],
            "plan_sha256": "old",
        }
        self.assertTrue(check_evidence(proof, "lab.yaml", "current", "runtime", "new"))
        self.assertEqual(check_evidence(proof, "lab.yaml", "current", "runtime", "old"), [])


class WebhookQuality(unittest.TestCase):
    def setUp(self):
        self.server = receiver.make_server(("127.0.0.1", 0), "test-secret-only")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def test_http_acceptance_probe(self):
        self.assertEqual(len(probe.run(self.url, "test-secret-only")), 6)

    def test_secret_is_required(self):
        with self.assertRaises(ValueError):
            receiver.make_server(("127.0.0.1", 0), "")

    def test_non_ascii_authorization_is_rejected_without_crashing(self):
        request = Request(
            self.url + "/events",
            b"{}",
            headers={"Authorization": "Bearer inv\u00e1lid", "Content-Type": "application/json"},
        )
        with self.assertRaises(HTTPError) as context:
            urlopen(request, timeout=5)
        self.assertEqual(context.exception.code, 401)

    def test_malformed_and_oversized_bodies(self):
        for data, status in [(b"{", 400), (b"x" * 8193, 413)]:
            request = Request(
                self.url + "/events",
                data,
                headers={
                    "Authorization": "Bearer test-secret-only",
                    "Content-Type": "application/json",
                },
            )
            with self.assertRaises(HTTPError) as context:
                urlopen(request, timeout=5)
            self.assertEqual(context.exception.code, status)

    def test_unknown_routes(self):
        with self.assertRaises(HTTPError) as context:
            urlopen(self.url + "/missing", timeout=5)
        self.assertEqual(context.exception.code, 404)

    def test_non_object_payload_is_rejected(self):
        for value in [None, [], True, {"device": ["R1"]}]:
            self.assertFalse(receiver.validate_intent(value))


if __name__ == "__main__":
    unittest.main()
