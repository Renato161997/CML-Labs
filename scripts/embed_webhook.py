"""Refresh/check registered example sources embedded in offline Ubuntu labs."""

import argparse
import base64
import json
import re
import sys
import textwrap

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
    "ssh-policy": {
        "/opt/cml-management/ssh_probe.py": "examples/management/ssh_probe.py",
        "/opt/cml-management/ssh_policy_probe.py": "examples/management/ssh_policy_probe.py",
    },
    "secure-management": {
        "/opt/cml-management/ssh_probe.py": "examples/management/ssh_probe.py",
        "/opt/cml-management/ssh_policy_probe.py": "examples/management/ssh_policy_probe.py",
    },
}

NATIVE_PROFILES = {
    "native-packet-mirror": {
        "INSIDE": {"/lab/t.py": "examples/security/traffic_fixture.py"},
        "OUTSIDE": {"/lab/t.py": "examples/security/traffic_fixture.py"},
        "CAPTURE": {"/lab/p.py": "examples/security/packet_observer.py"},
    },
    "native-flow-packet": {
        "INSIDE": {
            "/lab/t.py": "examples/security/traffic_fixture.py",
            "/lab/f.py": "examples/security/netflow_fixture.py",
        },
        "OUTSIDE": {
            "/lab/t.py": "examples/security/traffic_fixture.py",
            "/lab/f.py": "examples/security/netflow_fixture.py",
        },
        "CAPTURE": {"/lab/p.py": "examples/security/packet_observer.py"},
    },
    "native-qos-flow": {
        "INSIDE": {
            "/lab/t.py": "examples/security/traffic_fixture.py",
            "/lab/f.py": "examples/security/netflow_fixture.py",
        },
        "OUTSIDE": {
            "/lab/t.py": "examples/security/traffic_fixture.py",
            "/lab/f.py": "examples/security/netflow_fixture.py",
            "/lab/q.py": "examples/security/qos_observer.py",
            "/lab/netflow_fixture.py": "examples/security/netflow_fixture.py",
        },
    },
    "native-netflow": {
        "INSIDE": {
            "/lab/t.py": "examples/security/traffic_fixture.py",
            "/lab/f.py": "examples/security/netflow_fixture.py",
        },
        "OUTSIDE": {
            "/lab/t.py": "examples/security/traffic_fixture.py",
            "/lab/f.py": "examples/security/netflow_fixture.py",
        },
    },
    "native-firewall-traffic": {
        "INSIDE": {"/lab/t.py": "examples/security/traffic_fixture.py"},
        "OUTSIDE": {"/lab/t.py": "examples/security/traffic_fixture.py"},
    },
    "native-security-workbench": {
        "WORKBENCH": {
            "/lab/workbench.py": "examples/security/security_workbench.py",
        },
    },
    "secure-management": {
        "TOOLS": {
            "/lab/snmp_probe.py": "examples/management/snmp_probe.py",
            "/lab/snmp_identity_probe.py": "examples/management/snmp_identity_probe.py",
        },
    },
    "native-iosxe-gitops": {
        "TOOLS": {
            "/lab/api_probe.py": "examples/automation/api_probe.py",
            "/lab/inventory_probe.py": "examples/automation/inventory_probe.py",
            "/lab/route_probe.py": "examples/automation/route_probe.py",
            "/lab/gitops_probe.py": "examples/automation/gitops_probe.py",
        },
    },
    "native-iosxe-ansible-routing": {
        "TOOLS": {
            "/lab/api_probe.py": "examples/automation/api_probe.py",
            "/lab/inventory_probe.py": "examples/automation/inventory_probe.py",
            "/lab/route_probe.py": "examples/automation/route_probe.py",
            "/lab/ansible_probe.py": "examples/automation/ansible_probe.py",
            "/lab/ansible_route.py": "examples/automation/ansible_route.py",
        },
    },
    "native-iosxe-ansible": {
        "TOOLS": {
            "/lab/api_probe.py": "examples/automation/api_probe.py",
            "/lab/ansible_probe.py": "examples/automation/ansible_probe.py",
        },
    },
    "native-iosxe-models": {
        "TOOLS": {
            "/lab/api_probe.py": "examples/automation/api_probe.py",
            "/lab/inventory_probe.py": "examples/automation/inventory_probe.py",
            "/lab/models_probe.py": "examples/automation/models_probe.py",
        },
    },
    "native-iosxe-interface": {
        "TOOLS": {
            "/lab/api_probe.py": "examples/automation/api_probe.py",
            "/lab/interface_probe.py": "examples/automation/interface_probe.py",
        },
    },
    "native-iosxe-routing": {
        "TOOLS": {
            "/lab/api_probe.py": "examples/automation/api_probe.py",
            "/lab/inventory_probe.py": "examples/automation/inventory_probe.py",
            "/lab/route_probe.py": "examples/automation/route_probe.py",
        },
    },
    "native-iosxe-inventory": {
        "TOOLS": {
            "/lab/api_probe.py": "examples/automation/api_probe.py",
            "/lab/inventory_probe.py": "examples/automation/inventory_probe.py",
        },
    },
    "native-iosxe-rest-change": {
        "TOOLS": {
            "/lab/api_probe.py": "examples/automation/api_probe.py",
            "/lab/rest_change.py": "examples/automation/rest_change.py",
        },
    },
    "native-iosxe-api": {
        "TOOLS": {"/lab/api_probe.py": "examples/automation/api_probe.py"},
    },
    "native-api-distribution": {
        "APP1": {
            "/lab/service.py": "examples/api-core/service.py",
            "/lab/start_backend.sh": "examples/api-core/start_backend.sh",
        },
        "APP2": {
            "/lab/service.py": "examples/api-core/service.py",
            "/lab/start_backend.sh": "examples/api-core/start_backend.sh",
        },
        "FRONT": {"/lab/frontend.py": "examples/api-core/frontend.py"},
        "CLIENT": {"/lab/distribution_probe.py": "examples/api-core/distribution_probe.py"},
    },
    "native-api-core": {
        "SERVER": {"/lab/service.py": "examples/api-core/service.py"},
        "CLIENT": {"/lab/client.py": "examples/api-core/client.py"},
    },
    "native-snmp": {
        "TOOLS": {"/lab/snmp_probe.py": "examples/management/snmp_probe.py"},
    },
    "native-siem": {
        "LOG": {
            "/lab/syslog_receiver.py": "examples/visibility/syslog_receiver.py",
            "/lab/correlate.py": "examples/visibility/correlate.py",
        },
    },
}


def native_sources(data, metadata):
    """Validate registered source payloads without executing a shell or guest code."""
    profile = NATIVE_PROFILES.get(metadata.get("example_profile"))
    if not profile:
        if any(
            entry.get("name") == "boot.sh" and "CML_EMBED_" in entry.get("content", "")
            for node in data["nodes"]
            for entry in node.get("configuration", [])
        ):
            raise ValueError("Native embedded source needs a registered example profile")
        return False
    changed = False
    nodes = {node["label"]: node for node in data["nodes"]}
    for label, sources in profile.items():
        if label not in nodes:
            raise ValueError("Missing registered native example node: " + label)
        boot = next(f for f in nodes[label]["configuration"] if f["name"] == "boot.sh")
        for filename, source in sources.items():
            marker = "CML_EMBED_" + re.sub(r"[^A-Z0-9]", "_", source.upper())
            header = "base64 -d > " + filename + " <<'" + marker + "'\n"
            pattern = re.escape(header) + r"([A-Za-z0-9+/=\n]+)\n" + re.escape(marker) + r"(?=\n|$)"
            match = re.search(pattern, boot["content"])
            if not match:
                raise ValueError("Missing native source payload: " + label + ":" + filename)
            decoded = base64.b64decode(match.group(1).replace("\n", ""), validate=True)
            expected = (ROOT / source).read_bytes()
            if decoded != expected:
                payload = "\n".join(textwrap.wrap(base64.b64encode(expected).decode(), 76))
                boot["content"] = (
                    boot["content"][: match.start(1)] + payload + boot["content"][match.end(1) :]
                )
                changed = True
    return changed


def update(check=False):
    changed = []
    for relative, metadata in json.loads(
        (ROOT / "catalog/curated.json").read_text(encoding="utf-8")
    ).items():
        path = ROOT / relative
        data = load(path)
        dirty = native_sources(data, metadata)
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
