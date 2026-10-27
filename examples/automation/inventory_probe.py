"""Collect and reconcile actual IOS XE RESTCONF facts; never fabricate empty success."""

import argparse
import json
from pathlib import Path

import requests
import yaml
from api_probe import AUTH, URL, rest


def collect(http):
    response = rest(http)
    assert response.status_code == 200
    name = response.json()["Cisco-IOS-XE-native:hostname"]
    response = http.get(
        URL.rsplit("/", 1)[0] + "/interface",
        auth=AUTH,
        verify="/lab/peer-ca.pem",
        headers={"Accept": "application/yang-data+json"},
        timeout=10,
        allow_redirects=False,
    )
    assert response.status_code == 200, response.status_code
    interfaces = response.json()["Cisco-IOS-XE-native:interface"]["GigabitEthernet"]
    management = next(item for item in interfaces if str(item["name"]) == "1")
    address = management["ip"]["address"]["primary"]["address"]
    mask = management["ip"]["address"]["primary"]["mask"]
    return {
        "hostname": name,
        "management_interface": "GigabitEthernet1",
        "ipv4": address,
        "mask": mask,
        "observed_gigabit_interfaces": len(interfaces),
    }


def run(mode, phase):
    with requests.Session() as http:
        http.trust_env = False
        facts = collect(http)
        assert (
            facts["hostname"] == "API"
            and facts["ipv4"] == "198.18.0.1"
            and facts["mask"] == "255.255.255.252"
        )
        if mode == "inventory":
            for suffix, payload in (
                ("json", json.dumps(facts, sort_keys=True)),
                ("yaml", yaml.safe_dump(facts, sort_keys=True)),
            ):
                Path("/lab/inventory." + suffix).write_text(payload)
            assert (
                json.loads(Path("/lab/inventory.json").read_text())
                == yaml.safe_load(Path("/lab/inventory.yaml").read_text())
                == facts
            )
            missing = http.get(
                URL.rsplit("/", 1)[0] + "/definitely-not-a-native-resource",
                auth=AUTH,
                verify="/lab/peer-ca.pem",
                timeout=10,
                allow_redirects=False,
            )
            assert missing.status_code == 404, (
                "Missing API resources must not turn into empty successful inventory"
            )
            return {
                "status": "passed",
                "actual_facts": facts,
                "json_yaml_roundtrip": True,
                "missing_resource_rejected": True,
            }
        desired = json.loads(Path("/lab/intent.json").read_text())
        assert set(desired) == {"hostname", "ipv4"} and desired["hostname"] == "API"
        differences = {
            key: {"expected": value, "observed": facts[key]}
            for key, value in desired.items()
            if facts[key] != value
        }
        assert set(differences) == ({"ipv4"} if phase == "drift" else set())
        return {
            "status": "passed",
            "structured_differences": differences,
            "live_hostname_control": facts["hostname"],
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("inventory", "validation"))
    parser.add_argument("phase", nargs="?", choices=("baseline", "drift", "recovered"))
    parser.add_argument("--set-intent", choices=("correct", "wrong"))
    args = parser.parse_args()
    if args.set_intent:
        Path("/lab/intent.json").write_text(
            json.dumps(
                {
                    "hostname": "API",
                    "ipv4": "192.0.2.99" if args.set_intent == "wrong" else "198.18.0.1",
                }
            )
        )
        print(json.dumps({"status": "configured", "intent": args.set_intent}))
    else:
        if not args.mode or not args.phase:
            parser.error("mode and phase are required")
        print(json.dumps(run(args.mode, args.phase), sort_keys=True))
