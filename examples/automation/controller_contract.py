"""Small, explicit contract for the offline device-backed controller exercise."""

import json
import re

TOKEN = "Cml-Controller-Only-983"  # Public classroom fixture, not a production secret.
MARKER = "CML-DEVICE-CONTROLLER-V1"
GOOD = "198.18.0.2"
BAD = "198.18.0.99"
FIELDS = {"request_id", "device", "prefix", "next_hop", "state"}


def intent(request_id, state="present"):
    return validate(
        {
            "request_id": request_id,
            "device": "API",
            "prefix": "192.0.2.42/32",
            "next_hop": GOOD,
            "state": state,
        }
    )


def validate(value):
    if (
        not isinstance(value, dict)
        or set(value) != FIELDS
        or any(type(item) is not str for item in value.values())
    ):
        raise ValueError("Unexpected intent shape or scalar types")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,39}", value["request_id"]):
        raise ValueError("Invalid request identifier")
    if (value["device"], value["prefix"], value["next_hop"]) != (
        "API",
        "192.0.2.42/32",
        GOOD,
    ) or value["state"] not in ("present", "absent"):
        raise ValueError("Only the declared classroom route and next hop may be changed")
    return dict(value)


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def decode(value):
    return json.loads(value, object_pairs_hook=unique_fields)


def approvals():
    return [
        intent("install-1"),
        intent("repair-1"),
        intent("withdraw-1", "absent"),
        intent("rollback-1", "absent"),
    ]
