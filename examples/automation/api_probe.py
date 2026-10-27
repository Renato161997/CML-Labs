"""Verified RESTCONF and NETCONF checks against the isolated IOS XE API guest."""

import argparse
import json
import time
from pathlib import Path
from xml.etree import ElementTree

import paramiko
import requests
from ncclient import manager
from ncclient.devices.iosxe import IosxeDeviceHandler
from ncclient.transport.errors import AuthenticationError, SessionCloseError, SSHUnknownHostError

HOST = "198.18.0.1"
NAMESPACE = "http://cisco.com/ns/yang/Cisco-IOS-XE-native"
URL = "https://api.cml-lab.example/restconf/data/Cisco-IOS-XE-native:native/hostname"
AUTH = ("CML-LAB", "Cml-lab-only-984")  # Public isolated-lab fixture.


class StrictIOSXE(IosxeDeviceHandler):
    def add_additional_ssh_connect_params(self, kwargs):
        # ncclient 0.6.17's stock IOS XE hook otherwise accepts unknown keys.
        kwargs["unknown_host_cb"] = lambda *_: False


def connection_options():
    peer = json.loads(Path("/lab/peer-ssh.json").read_text())
    if peer["host"] != HOST or peer["port"] != 830:
        raise ValueError("This fixture only connects to its own benchmark-address peer")
    return {
        "host": HOST,
        "port": 830,
        "username": AUTH[0],
        "password": AUTH[1],
        "hostkey_verify": True,
        "hostkey_b64": peer["hostkey_b64"],
        "look_for_keys": False,
        "allow_agent": False,
        "device_params": {"handler": StrictIOSXE},
        "timeout": 20,
    }


def hostname(session):
    subtree = '<native xmlns="' + NAMESPACE + '"><hostname/></native>'
    data = session.get_config(source="running", filter=("subtree", subtree)).data_xml
    return ElementTree.fromstring(data).find(".//{" + NAMESPACE + "}hostname").text


def connect_verified(options):
    deadline = time.monotonic() + 45
    while True:
        try:
            return manager.connect(**options)
        except SessionCloseError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)


def hostname_config(value):
    if value not in ("API", "API-CHANGED"):
        raise ValueError("Unexpected training hostname")
    return (
        '<config><native xmlns="'
        + NAMESPACE
        + '"><hostname>'
        + value
        + "</hostname></native></config>"
    )


def rest(session, auth=AUTH):
    deadline = time.monotonic() + 45
    while True:
        response = session.get(
            URL,
            auth=auth,
            verify="/lab/peer-ca.pem",
            headers={"Accept": "application/yang-data+json"},
            timeout=5,
            allow_redirects=False,
        )
        if response.status_code not in (404, 502, 503, 504) or time.monotonic() >= deadline:
            return response
        time.sleep(2)


def trust_negatives(http, options):
    assert rest(http, (AUTH[0], "wrong-public-training-fixture")).status_code in (401, 403)
    try:
        http.get(
            URL.replace("api.cml-lab.example", "wrong.cml-lab.example"),
            auth=AUTH,
            verify="/lab/peer-ca.pem",
            timeout=5,
        )
    except requests.exceptions.SSLError:
        pass
    else:
        raise AssertionError("TLS hostname mismatch was accepted")
    try:
        with manager.connect(**dict(options, password="wrong-public-training-fixture")):
            raise AssertionError("NETCONF accepted incorrect credentials")
    except AuthenticationError:
        pass
    false_key = paramiko.RSAKey.generate(2048).get_base64()
    try:
        with manager.connect(**dict(options, hostkey_b64=false_key)):
            raise AssertionError("NETCONF accepted a mismatching pinned host key")
    except SSHUnknownHostError:
        pass


def run(mode, phase):
    options = connection_options()
    with requests.Session() as http:
        http.trust_env = False
        if phase != "https-off":
            response = rest(http)
            assert response.status_code == 200 and response.json() == {
                "Cisco-IOS-XE-native:hostname": "API"
            }
        with connect_verified(options) as session:
            assert hostname(session) == "API"
            if phase == "https-off":
                try:
                    http.get(URL, auth=AUTH, verify="/lab/peer-ca.pem", timeout=5)
                except requests.exceptions.SSLError:
                    raise
                except requests.exceptions.ConnectionError:
                    pass
                else:
                    raise AssertionError("HTTPS unexpectedly remained reachable")
                return {
                    "status": "passed",
                    "mode": mode,
                    "phase": phase,
                    "netconf_still_usable": True,
                }
            if mode == "manage":
                try:
                    assert session.edit_config(
                        target="running", config=hostname_config("API-CHANGED")
                    ).ok
                    assert hostname(session) == "API-CHANGED"
                finally:
                    assert session.edit_config(target="running", config=hostname_config("API")).ok
                assert hostname(session) == "API"
            elif mode == "yang":
                assert any(
                    "Cisco-IOS-XE-native" in capability
                    for capability in session.server_capabilities
                )
                schema = session.get_schema("Cisco-IOS-XE-native").data
                assert "module Cisco-IOS-XE-native" in schema and NAMESPACE in schema
        trust_negatives(http, options)
        with manager.connect(**options) as session:
            assert hostname(session) == "API"
    return {
        "status": "passed",
        "mode": mode,
        "phase": phase,
        "tls_hostname_verified": True,
        "ssh_key_pinned_from_serial": True,
        "wrong_credentials_and_keys_rejected": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("manage", "yang"))
    parser.add_argument("phase", choices=("baseline", "https-off", "recovered"))
    args = parser.parse_args()
    print(json.dumps(run(args.mode, args.phase), sort_keys=True))
