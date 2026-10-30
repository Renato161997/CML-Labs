"""Generate a separate isolated inspection node without changing stock definitions."""

import argparse
import re
from pathlib import Path

import yaml
from toolbox_assets import definitions as toolbox_definitions
from toolbox_assets import docker_image_digest

KIND = "cml-labs-inspection"


def definitions(image, archive, digest):
    if not re.fullmatch(r"cml-labs-inspection:[0-9a-f]{12}", image):
        raise ValueError("Expected an immutable inspection source-revision tag")
    suffix = image.split(":")[1]
    if archive != f"{KIND}-{suffix}.tar.gz":
        raise ValueError("Inspection archive and image revision must match")
    node, image_def = toolbox_definitions(
        "cml-labs-toolbox:" + suffix, "cml-labs-toolbox-" + suffix + ".tar.gz", digest
    )
    node["id"] = KIND
    node["general"]["description"] = "Isolated Snort3 packet-inspection teaching guest"
    node["ui"].update(
        label="CML-Labs Inspection",
        label_prefix="inspection-",
        description="Snort3 signature actions on isolated fixture traffic",
    )
    import json

    config = node["configuration"]["provisioning"]["files"][0]
    parsed = json.loads(config["content"])
    parsed["docker"]["caps"] = ["NET_ADMIN", "NET_RAW"]
    parsed["shell"] = "/bin/bash"
    config["content"] = json.dumps(parsed, indent=2) + "\n"
    image_def.update(
        id=KIND + "-" + suffix,
        node_definition_id=KIND,
        description="Digest-pinned Cisco Talos Snort3 derivative; isolated root guest",
        label="Inspection " + suffix,
        disk_image=archive,
        docker_tag=image,
    )
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
    for name, data in (("node-definition.yaml", node), ("image-definition.yaml", image)):
        (args.output / name).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
