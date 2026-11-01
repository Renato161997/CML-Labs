import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from services_assets import definitions
from toolbox_assets import definitions as toolbox_definitions


class ServicesDefinitionTests(unittest.TestCase):
    def test_new_kind_and_archive_are_bound_to_same_revision(self):
        node, image = definitions(
            "cml-labs-services:123456abcdef",
            "cml-labs-services-123456abcdef.tar.gz",
            "a" * 64,
        )
        self.assertEqual(node["id"], "cml-labs-services")
        self.assertEqual(image["node_definition_id"], node["id"])
        self.assertEqual(image["id"], "cml-labs-services-123456abcdef")
        self.assertEqual(image["disk_image"], "cml-labs-services-123456abcdef.tar.gz")
        self.assertEqual(image["sha256"], "a" * 64)

    def test_existing_toolbox_definition_and_capabilities_are_not_changed(self):
        args = ("cml-labs-toolbox:123456abcdef", "cml-labs-toolbox-123456abcdef.tar.gz", "a" * 64)
        before = toolbox_definitions(*args)
        node, _ = definitions(
            "cml-labs-services:123456abcdef", "cml-labs-services-123456abcdef.tar.gz", "a" * 64
        )
        after = toolbox_definitions(*args)
        self.assertEqual(before, after)
        original = json.loads(before[0]["configuration"]["provisioning"]["files"][0]["content"])
        derived = json.loads(node["configuration"]["provisioning"]["files"][0]["content"])
        self.assertEqual(original["docker"], derived["docker"])
        self.assertNotIn("SYS_ADMIN", derived["docker"]["caps"])

    def test_wrong_kind_revision_archive_or_digest_rejected(self):
        for tag, archive, digest in (
            ("cml-labs-toolbox:123456abcdef", "cml-labs-services-123456abcdef.tar.gz", "a" * 64),
            ("cml-labs-services:latest", "cml-labs-services-latest.tar.gz", "a" * 64),
            ("cml-labs-services:123456abcdef", "cml-labs-services-abcdef123456.tar.gz", "a" * 64),
            ("cml-labs-services:123456abcdef", "../image.tar.gz", "a" * 64),
            ("cml-labs-services:123456abcdef", "cml-labs-services-123456abcdef.tar.gz", "invalid"),
        ):
            with self.subTest(tag=tag, archive=archive), self.assertRaises(ValueError):
                definitions(tag, archive, digest)


if __name__ == "__main__":
    unittest.main()
