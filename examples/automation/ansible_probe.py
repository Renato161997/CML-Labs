"""Run real Ansible NETCONF tasks with a serial-pinned trust store and rollback."""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree

import paramiko
import requests
import yaml
from api_probe import (
    AUTH,
    HOST,
    NAMESPACE,
    connect_verified,
    connection_options,
    hostname,
    hostname_config,
    rest,
)


def get_task(register):
    return {
        "name": "Read actual hostname",
        "ansible.netcommon.netconf_get": {
            "source": "running",
            "display": "xml",
            "filter": '<native xmlns="' + NAMESPACE + '"><hostname/></native>',
        },
        "register": register,
    }


def copy_task(register, name):
    return {
        "name": "Keep independent observed XML",
        "ansible.builtin.copy": {
            "content": "{{ " + register + ".stdout }}",
            "dest": "/lab/ansible-" + name + ".xml",
            "mode": "0600",
        },
        "delegate_to": "localhost",
        "vars": {"ansible_connection": "local"},
    }


def edit_task(value):
    content = ElementTree.fromstring(hostname_config(value))
    content.tag = "{urn:ietf:params:xml:ns:netconf:base:1.0}config"
    return {
        "name": "Set only the training hostname",
        "ansible.netcommon.netconf_config": {
            "target": "running",
            "content": ElementTree.tostring(content, encoding="unicode"),
        },
    }


def execute(play, inventory, tag):
    play_path = Path("/lab/ansible-play.yml")
    play_path.write_text(yaml.safe_dump(play, sort_keys=False))
    inventory_path = Path("/lab/ansible-inventory.yml")
    inventory_path.write_text(yaml.safe_dump(inventory, sort_keys=False))
    environment = dict(
        os.environ,
        ANSIBLE_HOST_KEY_CHECKING="True",
        ANSIBLE_PARAMIKO_LOOK_FOR_KEYS="False",
        ANSIBLE_NOCOLOR="True",
        ANSIBLE_PERSISTENT_CONNECT_TIMEOUT="15",
        ANSIBLE_PERSISTENT_COMMAND_TIMEOUT="15",
    )
    environment.pop("SSH_AUTH_SOCK", None)
    listed = subprocess.run(
        ["ansible-inventory", "-i", str(inventory_path), "--list"],
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert listed.returncode == 0
    hostvars = json.loads(listed.stdout)["_meta"]["hostvars"]["api"]
    assert hostvars["ansible_host"] == HOST and hostvars["ansible_port"] == 830
    assert hostvars["ansible_connection"] == "ansible.netcommon.netconf"
    assert hostvars["ansible_host_key_checking"] is True
    with tempfile.TemporaryDirectory(prefix="ansible-ctl-", dir="/lab") as control:
        environment["ANSIBLE_PERSISTENT_CONTROL_PATH_DIR"] = control
        log_path = Path("/lab/ansible-" + tag + ".log")
        arguments = ["ansible-playbook", "-i", str(inventory_path), str(play_path)]
        # Persistent connection daemons must not keep a captured stdout pipe open.
        with log_path.open("w") as stream:
            try:
                result = subprocess.run(
                    arguments,
                    env=environment,
                    text=True,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=60,
                )
            except subprocess.TimeoutExpired as exc:
                stream.flush()
                raise TimeoutError(
                    "Ansible exceeded 60 seconds: " + log_path.read_text()[-2000:]
                ) from exc
    return subprocess.CompletedProcess(arguments, result.returncode, log_path.read_text(), "")


def run(mode):
    peer = json.loads(Path("/lab/peer-ssh.json").read_text())
    assert peer["host"] == HOST and peer["port"] == 830
    known_hosts = Path("/root/.ssh/known_hosts")
    assert not known_hosts.exists() or not known_hosts.read_text().strip(), (
        "Refuse to replace an existing trust store"
    )
    original_store = known_hosts.read_bytes() if known_hosts.exists() else None
    known_hosts.parent.mkdir(mode=0o700, exist_ok=True)
    pin = f"{HOST},[{HOST}]:830 ssh-rsa {peer['hostkey_b64']}\n"
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
    read_only = [
        {
            "name": "NETCONF inventory",
            "hosts": "api",
            "gather_facts": False,
            "tasks": [get_task("before"), copy_task("before", "before")],
        }
    ]
    changes = [
        {
            "name": "NETCONF baseline with rollback",
            "hosts": "api",
            "gather_facts": False,
            "tasks": [
                {
                    "block": [
                        get_task("before"),
                        copy_task("before", "before"),
                        edit_task("API-CHANGED"),
                        get_task("changed"),
                        copy_task("changed", "changed"),
                        edit_task("API-CHANGED"),
                        get_task("repeated"),
                        copy_task("repeated", "repeated"),
                    ],
                    "always": [edit_task("API")],
                }
            ],
        }
    ]
    try:
        known_hosts.write_text(pin)
        with requests.Session() as http:
            http.trust_env = False
            assert rest(http).status_code == 200
        with connect_verified(connection_options()) as session:
            assert hostname(session) == "API"
        result = execute(read_only if mode == "inventory" else changes, inventory, "positive")
        assert result.returncode == 0, (result.stdout + result.stderr)[-2500:]
        for name, expected in (
            (("before", "API"),)
            if mode == "inventory"
            else (("before", "API"), ("changed", "API-CHANGED"), ("repeated", "API-CHANGED"))
        ):
            document = ElementTree.fromstring(Path("/lab/ansible-" + name + ".xml").read_text())
            assert document.findtext(".//{*}hostname") == expected
        known_hosts.write_text(
            f"{HOST},[{HOST}]:830 ssh-rsa {paramiko.RSAKey.generate(2048).get_base64()}\n"
        )
        negative = execute(read_only, inventory, "wrong-key")
        assert negative.returncode != 0
        assert re.search(
            r"(?i)(unknown host key|host key[^\n]*(?:mismatch|does not match|not verified|could not be verified)|not found in known_hosts)",
            negative.stdout + negative.stderr,
        ), "Wrong-key failure must be identity-specific"
        known_hosts.write_text(pin)
        with connect_verified(connection_options()) as session:
            assert hostname(session) == "API"
    finally:
        try:
            known_hosts.write_text(pin)
            with connect_verified(connection_options()) as session:
                if mode == "change":
                    assert session.edit_config(target="running", config=hostname_config("API")).ok
                assert hostname(session) == "API"
        finally:
            if original_store is None:
                known_hosts.unlink(missing_ok=True)
            else:
                known_hosts.write_bytes(original_store)
    return {
        "status": "passed",
        "mode": mode,
        "real_ansible_netconf": True,
        "host_key_verified_from_serial": True,
        "wrong_key_rejected": True,
        "fresh_control_socket_per_run": True,
        "hostname_restored": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inventory", "change"))
    print(json.dumps(run(parser.parse_args().mode), sort_keys=True))
