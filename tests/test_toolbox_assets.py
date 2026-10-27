import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from toolbox_assets import definitions, docker_image_digest


class ToolboxDefinitionsTests(unittest.TestCase):
    def test_docker_config_digest_is_not_archive_checksum(self):
        tag = "cml-labs-toolbox:abcdef123456"
        config = json.dumps({"architecture": "amd64", "os": "linux"}).encode()
        expected = hashlib.sha256(config).hexdigest()
        for name in (expected + ".json", "blobs/sha256/" + expected):
            with self.subTest(layout=name), tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / "image.tar.gz"
                with tarfile.open(archive, "w:gz") as package:
                    manifest = json.dumps([{"Config": name, "RepoTags": [tag]}]).encode()
                    for filename, data in (("manifest.json", manifest), (name, config)):
                        info = tarfile.TarInfo(filename)
                        info.size = len(data)
                        package.addfile(info, io.BytesIO(data))
                self.assertEqual(docker_image_digest(archive, tag), expected)
                self.assertNotEqual(expected, hashlib.sha256(archive.read_bytes()).hexdigest())
                with self.assertRaises(ValueError):
                    docker_image_digest(archive, "cml-labs-toolbox:000000000000")

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
