"""Pinned OpenAPI exercise contract with real JSON Schema/HTTP observations."""

import argparse
import hashlib
import http.client
import http.server
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-OPENAPI-CONTRACT-V1"
SERVER = "198.18.0.1"
CLIENT = "198.18.0.2"
KEY = "Cml-Contract-Only-983"  # Public classroom fixture, never a production key.


def contract():
    device = {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "name", "interface"],
        "properties": {
            "id": {"type": "integer", "const": 1},
            "name": {"type": "string", "const": "fixture-1"},
            "interface": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "carrier"],
                "properties": {
                    "name": {"type": "string", "const": "eth1"},
                    "carrier": {"type": "boolean"},
                },
            },
        },
    }
    error = {
        "type": "object",
        "additionalProperties": False,
        "required": ["error"],
        "properties": {
            "error": {
                "type": "string",
                "enum": [
                    "authentication_required",
                    "device_not_found",
                    "invalid_parameter",
                    "method_not_allowed",
                ],
            }
        },
    }
    responses = {
        str(status): {
            "description": description,
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/" + ("Device" if status == 200 else "Error")
                    }
                }
            },
        }
        for status, description in (
            (200, "Actual fixture interface facts"),
            (400, "Invalid parameter"),
            (401, "Missing fixture key"),
            (404, "Unknown fixture device"),
        )
    }
    return {
        "openapi": "3.1.1",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {"title": "CML interface contract fixture", "version": "1.0.0"},
        "servers": [{"url": "http://198.18.0.1:8080"}],
        "security": [{"LabKey": []}],
        "paths": {
            "/devices/{device_id}": {
                "get": {
                    "operationId": "getFixtureDevice",
                    "parameters": [
                        {
                            "name": "device_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer", "minimum": 1, "maximum": 99},
                        }
                    ],
                    "responses": responses,
                }
            }
        },
        "components": {
            "securitySchemes": {"LabKey": {"type": "apiKey", "in": "header", "name": "X-Lab-Key"}},
            "schemas": {"Device": device, "Error": error},
        },
    }


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def bad_constant(value):
    raise ValueError("Non-JSON numeric constant")


def decoded(raw):
    if not 1 <= len(raw) <= 32768:
        raise ValueError("Response outside bounded size")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=bad_constant)


def schema_check(document, status, body):
    from jsonschema import Draft202012Validator

    responses = document["paths"]["/devices/{device_id}"]["get"]["responses"]
    if str(status) not in responses:
        raise ValueError("Undocumented response status")
    reference = responses[str(status)]["content"]["application/json"]["schema"]["$ref"]
    expected = "#/components/schemas/" + ("Device" if status == 200 else "Error")
    if reference != expected:
        raise ValueError("Only the pinned local schema reference is accepted")
    schema = document["components"]["schemas"][reference.rsplit("/", 1)[1]]
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(body)


def request(path, method="GET", authenticated=True):
    connection = http.client.HTTPConnection(SERVER, 8080, timeout=3)
    try:
        headers = {"X-Lab-Key": KEY} if authenticated else {}
        connection.request(method, path, headers=headers)
        response = connection.getresponse()
        raw = response.read(32769)
        return response.status, response.getheader("Content-Type"), response.getheader("Allow"), raw
    finally:
        connection.close()


def verify(path="/devices/1", authenticated=True):
    from jsonschema import ValidationError

    try:
        status, media, _, raw = request("/openapi.json")
        document = decoded(raw)
        if (
            status != 200
            or media != "application/json"
            or hashlib.sha256(encoded(document)).digest()
            != hashlib.sha256(encoded(contract())).digest()
        ):
            return {"accepted": False, "reason": "document_changed"}
        status, media, _, raw = request(path, authenticated=authenticated)
        if media != "application/json":
            return {"accepted": False, "reason": "unexpected_media", "wire_status": status}
        body = decoded(raw)
        try:
            schema_check(document, status, body)
        except ValidationError:
            return {"accepted": False, "reason": "schema_violation", "wire_status": status}
        except ValueError:
            return {"accepted": False, "reason": "undocumented_status", "wire_status": status}
        return {"accepted": True, "wire_status": status, "body": body}
    except (OSError, ValueError, TypeError, KeyError, http.client.HTTPException):
        return {"accepted": False, "reason": "unusable_response"}


def facts():
    carrier = Path("/sys/class/net/eth1/carrier").read_text().strip() == "1"
    return {"id": 1, "name": "fixture-1", "interface": {"name": "eth1", "carrier": carrier}}


def make_server(address):
    class Handler(http.server.BaseHTTPRequestHandler):
        def respond(self, status, value, media="application/json", allow=None):
            raw = encoded(value)
            self.send_response(status)
            self.send_header("Content-Type", media)
            self.send_header("Content-Length", str(len(raw)))
            if allow:
                self.send_header("Allow", allow)
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            self.respond(405, {"error": "method_not_allowed"}, allow="GET")

        def do_GET(self):
            mode = (ROOT / "api-mode").read_text().strip()
            if self.path == "/openapi.json":
                document = contract()
                if mode == "contract":
                    document["info"]["version"] = "2.0.0"
                self.respond(200, document)
                return
            if self.headers.get("X-Lab-Key") != KEY:
                self.respond(401, {"error": "authentication_required"})
                return
            match = re.fullmatch(r"/devices/([0-9]+)", self.path)
            if not match or not 1 <= int(match[1]) <= 99:
                self.respond(400, {"error": "invalid_parameter"})
                return
            if int(match[1]) != 1:
                self.respond(404, {"error": "device_not_found"})
                return
            value = facts()
            if mode == "schema":
                value["interface"]["carrier"] = "up"
            if mode == "lie":
                value["interface"]["carrier"] = False
            self.respond(
                201 if mode == "status" else 200,
                value,
                "text/plain" if mode == "media" else "application/json",
            )

        def log_message(self, *args):
            pass

    return http.server.HTTPServer(address, Handler)


def configure(role):
    address = SERVER if role == "SERVER" else CLIENT
    subprocess.run(
        ["ip", "addr", "add", address + "/30", "dev", "eth1"], check=True, capture_output=True
    )
    subprocess.run(["ip", "link", "set", "eth1", "up"], check=True, capture_output=True)
    if role == "SERVER":
        (ROOT / "api-mode").write_text("good")
        with (ROOT / "api-http.log").open("ab") as output:
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "serve"],
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    return {"status": "passed", "configured": role}


def probe(phase):
    if phase == "auth-errors":
        for path, authenticated, status in (
            ("/devices/1", False, 401),
            ("/devices/99", True, 404),
            ("/devices/invalid", True, 400),
        ):
            result = verify(path, authenticated)
            assert result["accepted"] and result["wire_status"] == status
        status, media, allow, raw = request("/devices/1", "POST")
        assert (status, media, allow) == (405, "application/json", "GET") and decoded(raw) == {
            "error": "method_not_allowed"
        }
        return {
            "status": "passed",
            "phase": phase,
            "documented_errors_validated": 3,
            "undocumented_method_rejected": True,
        }
    result = verify()
    if phase == "baseline":
        assert (
            result["accepted"]
            and result["wire_status"] == 200
            and result["body"]["interface"]["carrier"] is True
        )
    elif phase == "semantic-lie":
        assert result["accepted"] and result["body"]["interface"]["carrier"] is False
    else:
        expected = {
            "schema-bad": "schema_violation",
            "status-bad": "undocumented_status",
            "media-bad": "unexpected_media",
            "contract-bad": "document_changed",
        }
        assert phase in expected and not result["accepted"] and result["reason"] == expected[phase]
    return {
        "status": "passed",
        "phase": phase,
        "contract_accepted": result["accepted"],
        "schema_only_does_not_prove_truth": phase == "semantic-lie",
        "wire_status": result.get("wire_status"),
        "reason": result.get("reason"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "configure",
            "serve",
            "baseline",
            "auth-errors",
            "schema-bad",
            "status-bad",
            "media-bad",
            "contract-bad",
            "semantic-lie",
            "good",
            "schema",
            "status",
            "media",
            "contract",
            "lie",
        ),
    )
    action = parser.parse_args().action
    if os.geteuid() != 0 or (ROOT / "CML-OPENAPI-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the marked disposable contract fixture is accepted")
    role = (ROOT / "api-role").read_text().strip()
    assert role in ("SERVER", "CLIENT")
    if action == "configure":
        value = configure(role)
    elif action == "serve":
        assert role == "SERVER"
        make_server((SERVER, 8080)).serve_forever()
        return
    elif action in ("good", "schema", "status", "media", "contract", "lie"):
        assert role == "SERVER"
        (ROOT / "api-mode").write_text(action)
        value = {"status": "passed", "source_mode": action}
    else:
        assert role == "CLIENT"
        value = probe(action)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
