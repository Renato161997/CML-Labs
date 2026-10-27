"""Observe and repair one isolated IOS XE static route through trusted NETCONF."""

import argparse
import ipaddress
import json
from xml.etree import ElementTree

import requests
from api_probe import NAMESPACE, connect_verified, connection_options, hostname
from inventory_probe import collect

PREFIX = "192.0.2.42"
MASK = "255.255.255.255"
GOOD = "198.18.0.2"
BAD = "198.18.0.99"
BASE = "urn:ietf:params:xml:ns:netconf:base:1.0"


def route_config(operation, next_hop=None):
    if operation not in ("replace", "delete") or next_hop not in (None, GOOD, BAD):
        raise ValueError("Only the isolated exercise route can be changed")
    if operation == "replace" and next_hop is None:
        raise ValueError("Replacement requires a next hop")
    config = ElementTree.Element("config")
    native = ElementTree.SubElement(config, "{" + NAMESPACE + "}native")
    route = ElementTree.SubElement(ElementTree.SubElement(native, "ip"), "route")
    entry = ElementTree.SubElement(route, "ip-route-interface-forwarding-list")
    entry.set("{" + BASE + "}operation", operation)
    ElementTree.SubElement(entry, "prefix").text = PREFIX
    ElementTree.SubElement(entry, "mask").text = MASK
    if next_hop:
        forwarding = ElementTree.SubElement(entry, "fwd-list")
        ElementTree.SubElement(forwarding, "fwd").text = next_hop
    # Descendants must inherit the Cisco model namespace, not an unqualified one.
    for element in native.iter():
        if not element.tag.startswith("{"):
            element.tag = "{" + NAMESPACE + "}" + element.tag
    return ElementTree.tostring(config, encoding="unicode")


def observed_next_hops(session):
    subtree = '<native xmlns="' + NAMESPACE + '"><ip><route/></ip></native>'
    document = ElementTree.fromstring(
        session.get_config(source="running", filter=("subtree", subtree)).data_xml
    )
    result = []
    for entry in document.findall(".//{" + NAMESPACE + "}ip-route-interface-forwarding-list"):
        prefix = entry.findtext("{" + NAMESPACE + "}prefix")
        mask = entry.findtext("{" + NAMESPACE + "}mask")
        if prefix == PREFIX and mask == MASK:
            result.extend(child.text for child in entry.findall(".//{" + NAMESPACE + "}fwd"))
    return sorted(result)


def run(action):
    with requests.Session() as http:
        http.trust_env = False
        facts = collect(http)
    assert facts["hostname"] == "API" and facts["ipv4"] == "198.18.0.1"
    network = ipaddress.IPv4Interface(facts["ipv4"] + "/" + facts["mask"]).network
    with connect_verified(connection_options()) as session:
        if action in ("install", "wrong", "remove"):
            operation = "delete" if action == "remove" else "replace"
            hop = None if action == "remove" else BAD if action == "wrong" else GOOD
            assert session.edit_config(target="running", config=route_config(operation, hop)).ok
        hops = observed_next_hops(session)
        expected = (
            []
            if action in ("remove", "absent")
            else [BAD]
            if action in ("wrong", "diagnose")
            else [GOOD]
        )
        assert hops == expected, {"expected": expected, "observed": hops}
        off_link = [hop for hop in hops if ipaddress.IPv4Address(hop) not in network]
        assert off_link == ([BAD] if action in ("wrong", "diagnose") else [])
        assert hostname(session) == "API"
    return {
        "status": "passed",
        "action": action,
        "actual_next_hops": hops,
        "observed_management_network": str(network),
        "off_link_next_hops": off_link,
        "hostname_control": "API",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("install", "wrong", "remove", "present", "absent", "diagnose")
    )
    print(json.dumps(run(parser.parse_args().action), sort_keys=True))
