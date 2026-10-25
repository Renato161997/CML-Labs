"""Refresh/check registered example sources embedded in offline Ubuntu labs."""

import argparse
import base64
import json
import sys

import yaml
from labtools import ROOT, load

PROFILES = {
    "webhook": {
        "/opt/cml-webhook/receiver.py": "examples/webhook/receiver.py",
        "/opt/cml-webhook/probe.py": "examples/webhook/probe.py",
    },
    "ssh-management": {
        "/opt/cml-management/ssh_probe.py": "examples/management/ssh_probe.py",
    },
}


def update(check=False):
    changed = []
    for relative, metadata in json.loads(
        (ROOT / "catalog/curated.json").read_text(encoding="utf-8")
    ).items():
        path = ROOT / relative
        data = load(path)
        dirty = False
        for node in data["nodes"]:
            if node["node_definition"] != "ubuntu":
                continue
            userdata = next(f for f in node["configuration"] if f["name"] == "user-data")
            cloud = yaml.safe_load(userdata["content"])
            profile = metadata.get("example_profile", "webhook")
            if profile not in PROFILES:
                raise ValueError("Unknown embedded example profile: " + str(profile))
            files = {f["path"]: f for f in cloud.get("write_files", [])}
            for filename, source in PROFILES[profile].items():
                if filename not in files:
                    raise ValueError(relative + ": missing embedded source " + filename)
                entry = files[filename]
                expected = base64.b64encode((ROOT / source).read_bytes()).decode()
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
        "Embedded example sources are current"
        if not paths
        else "Updated " + str(len(paths)) + " topologies; refresh the catalog and live evidence"
    )
