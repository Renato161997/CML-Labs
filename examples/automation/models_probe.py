"""Round-trip real router facts and render validated network configuration data."""

import argparse
import ipaddress
import json
import re
from pathlib import Path

import requests
import yaml
from inventory_probe import collect
from jinja2 import Environment, StrictUndefined, UndefinedError


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError("Duplicate YAML field")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def validate(model):
    if not isinstance(model, dict) or set(model) != {"hostname", "interface", "address", "mask"}:
        raise ValueError("Unexpected model fields")
    if not all(isinstance(value, str) for value in model.values()):
        raise ValueError("Network model leaves must be strings")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,29}", model["hostname"]):
        raise ValueError("Unsafe hostname")
    if not re.fullmatch(r"GigabitEthernet[1-9][0-9]?", model["interface"]):
        raise ValueError("Unexpected interface name")
    ipaddress.IPv4Interface(model["address"] + "/" + model["mask"])
    return model


def run(mode):
    with requests.Session() as http:
        http.trust_env = False
        facts = collect(http)
        model = validate(
            {
                "hostname": facts["hostname"],
                "interface": facts["management_interface"],
                "address": facts["ipv4"],
                "mask": facts["mask"],
            }
        )
        encoded = json.dumps(model, sort_keys=True)
        encoded_yaml = yaml.safe_dump(model, sort_keys=True)
        assert (
            validate(json.loads(encoded))
            == validate(yaml.load(encoded_yaml, Loader=UniqueLoader))
            == model
        )
        Path("/lab/network-model.json").write_text(encoded)
        Path("/lab/network-model.yaml").write_text(encoded_yaml)
        for invalid in (
            dict(model, hostname="API\nno aaa new-model"),
            dict(model, address="999.1.1.1"),
            dict(model, mask=True),
            dict(model, command="erase startup-config"),
        ):
            try:
                validate(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid configuration data was accepted")
        for invalid in ("hostname: first\nhostname: second\n", "!!python/object:builtins.str {}"):
            try:
                yaml.load(invalid, Loader=UniqueLoader)
            except (ValueError, yaml.YAMLError):
                pass
            else:
                raise AssertionError("Ambiguous or unsafe YAML was accepted")
        if mode == "template":
            environment = Environment(
                undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True
            )
            template = environment.from_string(
                "hostname {{ hostname }}\ninterface {{ interface }}\n ip address {{ address }} {{ mask }}\n"
            )
            rendered = template.render(**model)
            assert (
                rendered
                == "hostname API\ninterface GigabitEthernet1\n ip address 198.18.0.1 255.255.255.252\n"
            )
            Path("/lab/rendered.cfg").write_text(rendered)
            try:
                template.render(hostname="API")
            except UndefinedError:
                pass
            else:
                raise AssertionError("Missing template input silently became empty configuration")
        assert collect(http) == facts, "Data transformation must not change device state"
    return {
        "status": "passed",
        "mode": mode,
        "facts": model,
        "roundtrip_lossless": True,
        "ambiguous_yaml_and_cli_injection_rejected": True,
        "device_writes": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("models", "template"))
    print(json.dumps(run(parser.parse_args().mode), sort_keys=True))
