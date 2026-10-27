"""Idempotent RESTCONF change, independent NETCONF readback and safe restoration."""

import json

import requests
from api_probe import AUTH, URL, connect_verified, connection_options, hostname, rest


def run():
    with requests.Session() as http:
        http.trust_env = False
        assert rest(http).status_code == 200
    with requests.Session() as http, connect_verified(connection_options()) as session:
        http.trust_env = False

        def replace(value):
            return http.put(
                URL,
                auth=AUTH,
                verify="/lab/peer-ca.pem",
                headers={
                    "Content-Type": "application/yang-data+json",
                    "Accept": "application/yang-data+json",
                },
                json={"Cisco-IOS-XE-native:hostname": value},
                timeout=10,
                allow_redirects=False,
            )

        assert rest(http).json() == {"Cisco-IOS-XE-native:hostname": "API"}
        try:
            for _ in range(2):
                response = replace("API-CHANGED")
                assert response.status_code in (200, 201, 204), (
                    response.status_code,
                    response.text[:400],
                )
                assert hostname(session) == "API-CHANGED"
                assert rest(http).json() == {"Cisco-IOS-XE-native:hostname": "API-CHANGED"}
            invalid = replace({"unexpected": "object-instead-of-string"})
            assert invalid.status_code in (400, 409, 422), invalid.status_code
            assert hostname(session) == "API-CHANGED", (
                "Rejected payload must not change the real device"
            )
        finally:
            restored = replace("API")
            assert restored.status_code in (200, 201, 204)
        assert hostname(session) == "API" and rest(http).json() == {
            "Cisco-IOS-XE-native:hostname": "API"
        }
    return {
        "status": "passed",
        "rest_put_idempotent": True,
        "independent_netconf_readback": True,
        "invalid_request_rejected": True,
        "finally_restored": True,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
