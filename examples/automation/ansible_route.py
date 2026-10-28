"""Apply the isolated host-route intent with real Ansible and independent NETCONF readback."""

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree

import requests
from ansible_probe import execute
from api_probe import AUTH, HOST, connect_verified, connection_options, hostname
from inventory_probe import collect
from route_probe import GOOD, observed_next_hops, route_config


def run(action):
    peer = json.loads(Path("/lab/peer-ssh.json").read_text())
    assert peer["host"] == HOST and peer["port"] == 830
    store = Path("/root/.ssh/known_hosts")
    original = store.read_bytes() if store.exists() else None
    assert original is None or not original.strip(), "Refuse an existing guest trust store"
    store.parent.mkdir(mode=0o700, exist_ok=True)
    inventory = {
        "all": {
            "hosts": {
                "api": {
                    "ansible_host": HOST,
                    "ansible_port": 830,
                    "ansible_user": AUTH[0],
                    "ansible_password": AUTH[1],
                    "ansible_connection": "ansible.netcommon.netconf",
                    "ansible_network_os": "ansible.netcommon.default",
                    "ansible_host_key_checking": True,
                }
            }
        }
    }
    succeeded = False
    before = None
    try:
        store.write_text(f"{HOST},[{HOST}]:830 ssh-rsa {peer['hostkey_b64']}\n")
        with requests.Session() as http:
            http.trust_env = False
            assert collect(http)["ipv4"] == "198.18.0.1"
        with connect_verified(connection_options()) as session:
            before = observed_next_hops(session)
            assert before in ([], [GOOD]), "Unexpected prior route intent"
            assert hostname(session) == "API"
        assert action == "install" or before == [GOOD], (
            "Withdraw only a route established by the exercise"
        )
        content = route_config("replace", GOOD) if action == "install" else route_config("delete")
        document = ElementTree.fromstring(content)
        document.tag = "{urn:ietf:params:xml:ns:netconf:base:1.0}config"
        content = ElementTree.tostring(document, encoding="unicode")
        play = [
            {
                "name": "Routing intent",
                "hosts": "api",
                "gather_facts": False,
                "tasks": [
                    {
                        "name": "Apply only the isolated /32 route",
                        "ansible.netcommon.netconf_config": {
                            "target": "running",
                            "content": content,
                        },
                    }
                ],
            }
        ]
        result = execute(play, inventory, "route-" + action)
        assert result.returncode == 0, (result.stdout + result.stderr)[-2500:]
        with connect_verified(connection_options()) as session:
            hops = observed_next_hops(session)
            assert hops == ([GOOD] if action == "install" else [])
            assert hostname(session) == "API"
        succeeded = True
        return {
            "status": "passed",
            "action": action,
            "real_ansible_route_change": True,
            "actual_next_hops": hops,
            "hostname_control": "API",
        }
    finally:
        try:
            if not succeeded and before is not None:
                with connect_verified(connection_options()) as session:
                    current = observed_next_hops(session)
                    if before == [GOOD]:
                        assert session.edit_config(
                            target="running", config=route_config("replace", GOOD)
                        ).ok
                    elif current:
                        assert session.edit_config(
                            target="running", config=route_config("delete")
                        ).ok
                    assert observed_next_hops(session) == before
        finally:
            if original is None:
                store.unlink(missing_ok=True)
            else:
                store.write_bytes(original)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "remove"))
    print(json.dumps(run(parser.parse_args().action), sort_keys=True))
