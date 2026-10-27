"""Create separate CML definitions for the open-source automation client."""

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path

import yaml

KIND = "cml-labs-toolbox"


def docker_image_digest(archive, image):
    """CML needs Docker's config digest, distinct from the archive checksum."""
    with tarfile.open(archive, "r:gz") as package:
        member = package.getmember("manifest.json")
        if not member.isfile() or member.size > 131072:
            raise ValueError("Invalid Docker manifest")
        manifest = json.load(package.extractfile(member))
        if (
            not isinstance(manifest, list)
            or len(manifest) != 1
            or manifest[0].get("RepoTags") != [image]
        ):
            raise ValueError("Archive must contain exactly the expected image tag")
        config = manifest[0].get("Config", "")
        if not re.fullmatch(r"(?:blobs/sha256/)?[0-9a-f]{64}(?:\.json)?", config):
            raise ValueError("Invalid Docker config path")
        member = package.getmember(config)
        if not member.isfile() or member.size > 1048576:
            raise ValueError("Invalid Docker config")
        raw = package.extractfile(member).read()
        digest = hashlib.sha256(raw).hexdigest()
        if config.split("/")[-1].removesuffix(".json") != digest:
            raise ValueError("Docker config content does not match its digest")
        metadata = json.loads(raw)
        if metadata.get("architecture") != "amd64" or metadata.get("os") != "linux":
            raise ValueError("Expected a linux/amd64 image")
        return digest


def definitions(image, archive, digest):
    """Only accept the project's versioned archive; never modify stock kinds."""
    if not re.fullmatch(r"cml-labs-toolbox:[0-9a-f]{12}", image):
        raise ValueError("Expected an immutable source-revision image tag")
    expected = "cml-labs-toolbox-" + image.split(":")[1] + ".tar.gz"
    if archive not in ("cml-labs-toolbox.tar.gz", expected) or not re.fullmatch(
        r"[0-9a-f]{64}", digest
    ):
        raise ValueError("Invalid archive name or SHA-256")
    docker = {
        "mounts": ["type=bind,source=cfg/boot.sh,target=/boot.sh"],
        "caps": [
            "CHOWN",
            "DAC_OVERRIDE",
            "FOWNER",
            "FSETID",
            "KILL",
            "NET_BIND_SERVICE",
            "NET_RAW",
            "SETFCAP",
            "SETGID",
            "SETPCAP",
            "SETUID",
            "SYS_CHROOT",
            "NET_ADMIN",
        ],
    }
    flags = {
        "ram": True,
        "cpus": True,
        "cpu_limit": True,
        "data_volume": False,
        "boot_disk_size": False,
    }
    node = {
        "id": KIND,
        "schema_version": "0.0.1",
        "boot": {"timeout": 60, "completed": ["READY"]},
        "general": {
            "description": "Open-source automation training client",
            "nature": "server",
            "read_only": False,
        },
        "sim": {
            "linux_native": {
                "driver": "server",
                "libvirt_domain_driver": "docker",
                "ram": 1024,
                "cpus": 1,
                "cpu_limit": 100,
            }
        },
        "configuration": {
            "generator": {"driver": None},
            "provisioning": {
                "volume_name": "cfg",
                "media_type": "raw",
                "files": [
                    {
                        "name": "config.json",
                        "editable": False,
                        "content": json.dumps(
                            {
                                "docker": docker,
                                "day0cmd": ["/bin/bash", "/boot.sh"],
                                "busybox": True,
                            },
                            indent=2,
                        )
                        + "\n",
                    },
                    {
                        "name": "boot.sh",
                        "editable": True,
                        "content": "#!/bin/bash\nset -e\necho READY >/dev/console\n",
                    },
                ],
            },
        },
        "device": {
            "interfaces": {
                "has_loopback_zero": False,
                "min_count": 1,
                "default_count": 4,
                "management": ["eth0"],
                "physical": ["eth0", "eth1", "eth2", "eth3"],
                "serial_ports": 1,
            }
        },
        "inherited": {"image": dict(flags), "node": dict(flags)},
        "pyats": {"os": "linux"},
        "ui": {
            "description": "Git, Ansible, NETCONF and verified HTTPS clients",
            "group": "Others",
            "icon": "server",
            "label": "CML-Labs Toolbox",
            "label_prefix": "toolbox-",
            "visible": True,
        },
    }
    image_def = {
        "id": KIND + "-" + image.split(":")[1],
        "node_definition_id": KIND,
        "schema_version": "0.0.1",
        "description": "Debian automation toolbox; package inventory accompanies release",
        "label": "Toolbox " + image.split(":")[1],
        "read_only": False,
        "ram": 1024,
        "cpus": 1,
        "cpu_limit": 100,
        "data_volume": None,
        "boot_disk_size": None,
        "disk_image": archive,
        "docker_tag": image,
        "sha256": digest,
    }
    return node, image_def


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    digest = docker_image_digest(args.archive, args.image)
    node, image = definitions(args.image, args.archive.name, digest)
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, data in (("node-definition.yaml", node), ("image-definition.yaml", image)):
        (args.output / filename).write_text(
            yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n"
        )


if __name__ == "__main__":
    main()
