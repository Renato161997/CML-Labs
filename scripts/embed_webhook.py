"""Refresh/check the example sources embedded in the two offline Ubuntu labs."""

import argparse
import base64
import json
import sys

import yaml
from labtools import ROOT, load


def update(check=False):
    changed = []
    for relative in json.loads((ROOT / "catalog/curated.json").read_text(encoding="utf-8")):
        path = ROOT / relative
        data = load(path)
        dirty = False
        for node in data["nodes"]:
            if node["node_definition"] != "ubuntu":
                continue
            userdata = next(f for f in node["configuration"] if f["name"] == "user-data")
            cloud = yaml.safe_load(userdata["content"])
            for filename in ("receiver.py", "probe.py"):
                entry = next(
                    f for f in cloud["write_files"] if f["path"] == "/opt/cml-webhook/" + filename
                )
                expected = base64.b64encode(
                    (ROOT / "examples/webhook" / filename).read_bytes()
                ).decode()
                if entry.get("encoding") != "b64" or entry["content"] != expected:
                    dirty = True
                    entry["encoding"] = "b64"
                    entry["content"] = expected
            if dirty:
                userdata["content"] = "#cloud-config\n" + yaml.safe_dump(cloud, sort_keys=False)
        if dirty:
            changed.append(relative)
            if not check:
                path.write_text(
                    yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
                    encoding="utf-8",
                    newline="\n",
                )
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    paths = update(check=args.check)
    if args.check and paths:
        print("Embedded example differs from source: " + ", ".join(paths), file=sys.stderr)
        sys.exit(1)
    print(
        "Embedded webhook sources are current"
        if not paths
        else "Updated " + str(len(paths)) + " topologies; refresh the catalog and live evidence"
    )
