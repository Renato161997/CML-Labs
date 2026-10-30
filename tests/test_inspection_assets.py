import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inspection_assets
import toolbox_assets


class InspectionAssetsTests(unittest.TestCase):
    def test_inspection_generation_does_not_change_toolbox_or_stock_identity(self):
        tag = "0123456789ab"
        digest = "a" * 64
        before = toolbox_assets.definitions(
            "cml-labs-toolbox:" + tag, "cml-labs-toolbox-" + tag + ".tar.gz", digest
        )
        node, image = inspection_assets.definitions(
            "cml-labs-inspection:" + tag, "cml-labs-inspection-" + tag + ".tar.gz", digest
        )
        after = toolbox_assets.definitions(
            "cml-labs-toolbox:" + tag, "cml-labs-toolbox-" + tag + ".tar.gz", digest
        )
        self.assertEqual(before, after)
        self.assertNotIn(node["id"], ("snort", "cml-labs-toolbox"))
        self.assertEqual(node["id"], image["node_definition_id"])
        config = json.loads(node["configuration"]["provisioning"]["files"][0]["content"])
        self.assertEqual(set(config["docker"]["caps"]), {"NET_ADMIN", "NET_RAW"})
        self.assertNotIn("privileged", config["docker"])
        self.assertTrue(all("docker.sock" not in mount for mount in config["docker"]["mounts"]))

    def test_conflicting_revision_paths_and_invalid_digests_are_rejected(self):
        for image, archive, digest in (
            ("snort:latest", "cml-labs-inspection-0123456789ab.tar.gz", "a" * 64),
            (
                "cml-labs-inspection:0123456789ab",
                "../cml-labs-inspection-0123456789ab.tar.gz",
                "a" * 64,
            ),
            (
                "cml-labs-inspection:0123456789ab",
                "cml-labs-inspection-ffffffffffff.tar.gz",
                "a" * 64,
            ),
            ("cml-labs-inspection:0123456789ab", "cml-labs-inspection-0123456789ab.tar.gz", "bad"),
        ):
            with self.subTest(image=image, archive=archive), self.assertRaises(ValueError):
                inspection_assets.definitions(image, archive, digest)
