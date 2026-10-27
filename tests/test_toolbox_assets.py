import json
import unittest

from toolbox_assets import definitions


class ToolboxDefinitionsTests(unittest.TestCase):
    def test_stock_defaults_and_host_access_are_not_changed(self):
        node, image = definitions(
            "cml-labs-toolbox:abcdef123456", "cml-labs-toolbox.tar.gz", "a" * 64
        )
        self.assertEqual(node["id"], "cml-labs-toolbox")
        self.assertEqual(image["node_definition_id"], node["id"])
        self.assertEqual(image["sha256"], "a" * 64)
        config = json.loads(node["configuration"]["provisioning"]["files"][0]["content"])
        self.assertEqual(
            config["docker"]["mounts"], ["type=bind,source=cfg/boot.sh,target=/boot.sh"]
        )
        self.assertNotIn("SYS_ADMIN", config["docker"]["caps"])
        self.assertNotIn("privileged", config["docker"])
        self.assertEqual(node["sim"]["linux_native"]["ram"], 1024)

    def test_mutable_tags_foreign_images_and_bad_digests_are_rejected(self):
        for image in ("cml-labs-toolbox:latest", "net-tools:abcdef123456", "cml-labs-toolbox:abc"):
            with self.assertRaises(ValueError):
                definitions(image, "cml-labs-toolbox.tar.gz", "a" * 64)
        with self.assertRaises(ValueError):
            definitions("cml-labs-toolbox:abcdef123456", "../foreign.tar.gz", "a" * 64)
        with self.assertRaises(ValueError):
            definitions("cml-labs-toolbox:abcdef123456", "cml-labs-toolbox.tar.gz", "not-a-digest")
