"""Change one disposable IOS XE loopback and verify its model and independent readback."""

import argparse
import json
import re
from xml.etree import ElementTree

import requests
from api_probe import AUTH, NAMESPACE, URL, connect_verified, connection_options, hostname, rest
from ncclient.operations.rpc import RPCError

NUMBER = "88"
ADDRESS = "203.0.113.88"
MASK = "255.255.255.255"
BASE = "urn:ietf:params:xml:ns:netconf:base:1.0"
ENDPOINT = URL.rsplit("/", 1)[0] + "/interface/Loopback=" + NUMBER


def config(delete=False, invalid=False):
    body = ElementTree.Element("config")
    native = ElementTree.SubElement(body, "{" + NAMESPACE + "}native")
    interface = ElementTree.SubElement(native, "{" + NAMESPACE + "}interface")
    loopback = ElementTree.SubElement(interface, "{" + NAMESPACE + "}Loopback")
    ElementTree.SubElement(loopback, "{" + NAMESPACE + "}name").text = NUMBER
    if delete:
        loopback.set("{" + BASE + "}operation", "delete")
    else:
        ElementTree.SubElement(loopback, "{" + NAMESPACE + "}description").text = "CML-MODEL-LAB"
        primary = loopback
        for tag in ("ip", "address", "primary"):
            primary = ElementTree.SubElement(primary, "{" + NAMESPACE + "}" + tag)
        ElementTree.SubElement(primary, "{" + NAMESPACE + "}address").text = (
            "999.0.0.1" if invalid else ADDRESS
        )
        ElementTree.SubElement(primary, "{" + NAMESPACE + "}mask").text = MASK
    return ElementTree.tostring(body, encoding="unicode")


def observe(http, session, present):
    subtree = (
        '<native xmlns="'
        + NAMESPACE
        + '"><interface><Loopback><name>88</name></Loopback></interface></native>'
    )
    data = ElementTree.fromstring(
        session.get_config(source="running", filter=("subtree", subtree)).data_xml
    )
    entry = data.find(".//{" + NAMESPACE + "}Loopback")
    response = http.get(
        ENDPOINT,
        auth=AUTH,
        verify="/lab/peer-ca.pem",
        headers={"Accept": "application/yang-data+json"},
        timeout=10,
        allow_redirects=False,
    )
    if not present:
        assert entry is None and response.status_code == 404
        return
    assert response.status_code == 200 and entry is not None
    assert entry.findtext(".//{" + NAMESPACE + "}primary/{" + NAMESPACE + "}address") == ADDRESS
    observed = response.json()["Cisco-IOS-XE-native:Loopback"]
    if isinstance(observed, list):
        assert len(observed) == 1
        item = observed[0]
    else:
        assert isinstance(observed, dict), "Selected RESTCONF entry must be an object"
        item = observed
    assert entry.findtext("{" + NAMESPACE + "}name") == NUMBER
    assert entry.findtext("{" + NAMESPACE + "}description") == "CML-MODEL-LAB"
    assert entry.findtext(".//{" + NAMESPACE + "}primary/{" + NAMESPACE + "}mask") == MASK
    assert str(item["name"]) == NUMBER
    assert item["description"] == "CML-MODEL-LAB"
    assert item["ip"]["address"]["primary"] == {"address": ADDRESS, "mask": MASK}


def run(mode):
    with requests.Session() as http:
        http.trust_env = False
        assert rest(http).status_code == 200
        with connect_verified(connection_options()) as session:
            assert hostname(session) == "API"
            observe(http, session, False)
            schema_id = None
            if mode == "schema":
                native = session.get_schema("Cisco-IOS-XE-native").data
                assert re.search(r"include\s+Cisco-IOS-XE-interfaces\s*[;{]", native)
                model = session.get_schema("Cisco-IOS-XE-interfaces").data
                assert re.search(r"submodule\s+Cisco-IOS-XE-interfaces\b", model)
                assert re.search(r"\blist\s+Loopback\b", model)
                schema_id = "Cisco-IOS-XE-interfaces"
            created = False
            try:
                assert session.edit_config(target="running", config=config()).ok
                created = True
                observe(http, session, True)
                assert session.edit_config(target="running", config=config()).ok
                observe(http, session, True)
                try:
                    session.edit_config(target="running", config=config(invalid=True))
                except RPCError:
                    pass
                else:
                    raise AssertionError("The device accepted an invalid IPv4 model leaf")
                observe(http, session, True)
            finally:
                if created:
                    assert session.edit_config(target="running", config=config(delete=True)).ok
            observe(http, session, False)
            assert hostname(session) == "API" and rest(http).status_code == 200
    return {
        "status": "passed",
        "mode": mode,
        "retrieved_interface_schema": schema_id,
        "actual_loopback": "Loopback88",
        "idempotent_write": True,
        "invalid_model_value_rejected": True,
        "restconf_netconf_agree": True,
        "loopback_removed": True,
        "management_unchanged": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("change", "schema"))
    print(json.dumps(run(parser.parse_args().mode), sort_keys=True))
