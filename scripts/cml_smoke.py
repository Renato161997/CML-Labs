"""Opt-in isolated CML import/functional checks; never modify existing labs.

Examples:
  python scripts/cml_smoke.py --url https://your-controller --phase import
  python scripts/cml_smoke.py --url https://your-controller --phase functional --lab 017-single-area

Requires requirements-runtime.txt and licensed, installed reference images.
Password comes from CML_PASSWORD or getpass. No credential is written to disk.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import ssl
import time
import uuid
from importlib.metadata import version as package_version
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

import paramiko
import yaml
from acceptance import CLI_ERROR, execute_plan, execute_prerequisites
from console_protocol import response_complete
from httpx import HTTPError
from labtools import (
    RAM_MIB,
    ROOT,
    config_signature,
    digest,
    graph_signature,
    load,
    plan_digest,
    validate,
)
from linux_console import NATIVE_CONSOLE_PORT, NATIVE_LINUX, establish_linux_shell
from readiness import (
    establish_ios_privilege,
    establish_ios_prompt,
    running_node_states,
    verify_unconfirmed_consoles,
)
from virl2_client import ClientLibrary
from virl2_client.exceptions import APIError
from websockets.sync.client import connect


class WebConsole:
    def send_raw(self, text):
        self.socket.send(text)

    def __init__(self, client, url, node):
        self.label = node.label
        pieces = urlsplit(url)
        address = urlunsplit(
            (
                "wss",
                pieces.netloc,
                "/ws/dispatch/frontend/console",
                urlencode(
                    {
                        "cml_client": "WebUI",
                        "action": "lab_exec",
                        "uuid": node.console_key(NATIVE_CONSOLE_PORT.get(node.node_definition, 0)),
                    }
                ),
                "",
            )
        )
        self.socket = connect(
            address,
            ssl=ssl.create_default_context(),
            proxy=None,
            open_timeout=20,
            ping_interval=None,
            close_timeout=3,
        )
        try:
            self.socket.send(json.dumps({"token": client.jwtoken}))
            prompt = self.read(8)
            self.socket.send("\x03\r")
            prompt += self.read(3)
            if node.node_definition in ("iosv", "iosvl2", "iol-xe", "ioll2-xe", "csr1000v"):
                prompt = establish_ios_prompt(
                    self.label,
                    prompt,
                    self.socket.send,
                    self.read,
                    timeout=600 if node.node_definition == "iosv" else 240,
                )
                establish_ios_privilege(self.label, self.socket.send, self.read)
                self.command("terminal length 0", 3)
                self.command("terminal width 511", 3)
            elif node.node_definition in NATIVE_LINUX:
                establish_linux_shell(self.label, self.socket.send, self.read)
            elif node.node_definition == "ubuntu":
                deadline = time.monotonic() + 120
                while not re.search(r"root@DEVBOX", prompt) and time.monotonic() < deadline:
                    self.socket.send("\r")
                    prompt += self.read(5)
                if not re.search(r"root@DEVBOX", prompt):
                    raise RuntimeError(
                        "Ubuntu serial console did not reach its isolated root shell"
                    )
        except BaseException:
            self.socket.close()
            raise

    def read(self, seconds, until_prompt=False, command=None):
        until = time.monotonic() + seconds
        last = time.monotonic()
        text = ""
        while time.monotonic() < until:
            try:
                data = self.socket.recv(timeout=0.3)
                text += data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
                last = time.monotonic()
            except TimeoutError:
                if text and time.monotonic() - last > 0.8 and not until_prompt:
                    break
            if command is not None and response_complete(text, command, self.label):
                break
            if (
                command is None
                and until_prompt
                and re.search(
                    r"(?m)^" + re.escape(self.label) + r"(?:\([^\n]*\))?[>#]\s*$",
                    text.replace("\r", ""),
                )
            ):
                break
        return re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text).replace("\r", "")

    def command(self, command, timeout=18):
        self.read(0.4)
        self.socket.send("\r" + command + "\r")
        output = self.read(timeout, until_prompt=True, command=command)
        if not response_complete(output, command, self.label):
            raise TimeoutError("Console response did not finish after command echo")
        return output

    def close(self):
        self.socket.close()


class SSHConsole:
    def send_raw(self, text):
        self.channel.sendall(text)

    def __init__(self, client, host, node, lab, known_hosts):
        self.label = node.label
        self.ssh = paramiko.SSHClient()
        self.ssh.load_host_keys(str(known_hosts))
        self.ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            self.ssh.connect(
                host,
                username=client.username,
                password=client.password,
                look_for_keys=False,
                allow_agent=False,
                timeout=20,
            )
            self.channel = self.ssh.get_transport().open_session()
            self.channel.get_pty(width=180, height=60)
            self.channel.exec_command(
                f"open /{lab.id}/{node.id}/{NATIVE_CONSOLE_PORT.get(node.node_definition, 0)}"
            )
            prompt = self.read(8)
            self.channel.send("\r")
            prompt += self.read(3)
            if node.node_definition in ("iosv", "iosvl2", "iol-xe", "ioll2-xe", "csr1000v"):
                prompt = establish_ios_prompt(
                    self.label,
                    prompt,
                    self.channel.send,
                    self.read,
                    timeout=600 if node.node_definition == "iosv" else 240,
                )
                establish_ios_privilege(self.label, self.channel.send, self.read)
                self.command("terminal length 0", 3)
                self.command("terminal width 511", 3)
            elif node.node_definition in NATIVE_LINUX:
                establish_linux_shell(self.label, self.channel.send, self.read)
            elif node.node_definition == "ubuntu":
                deadline = time.monotonic() + 120
                while not re.search(r"root@DEVBOX", prompt) and time.monotonic() < deadline:
                    self.channel.send("\r")
                    prompt += self.read(5)
                if not re.search(r"root@DEVBOX", prompt):
                    raise RuntimeError(
                        "Ubuntu serial console did not reach its isolated root shell"
                    )
        except BaseException:
            self.ssh.close()
            raise

    def read(self, seconds, until_prompt=False, command=None):
        until = time.monotonic() + seconds
        last = time.monotonic()
        text = ""
        while time.monotonic() < until:
            if self.channel.recv_ready():
                text += self.channel.recv(65535).decode("utf-8", errors="replace")
                last = time.monotonic()
            elif text and time.monotonic() - last > 0.8 and not until_prompt:
                break
            if command is not None and response_complete(text, command, self.label):
                break
            if (
                command is None
                and until_prompt
                and (
                    re.search(
                        r"(?m)^" + re.escape(self.label) + r"(?:\([^\n]*\))?[>#]\s*$",
                        text.replace("\r", ""),
                    )
                    or re.search(r"(?m)^root@DEVBOX:[^\n]*#\s*$", text.replace("\r", ""))
                )
            ):
                break
            time.sleep(0.05)
        return re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text).replace("\r", "")

    def command(self, command, timeout=18):
        self.read(0.4)
        self.channel.send("\r" + command + "\r")
        output = self.read(timeout, until_prompt=True, command=command)
        if not response_complete(output, command, self.label):
            raise TimeoutError("Console response did not finish after command echo")
        return output

    def close(self):
        self.ssh.close()


def topology_signature(data):
    # Existing-lab proof is semantic, not the timestamp/order of an exported YAML document.
    return json.dumps({"nodes": data["nodes"], "links": data["links"]}, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--username", default=os.environ.get("CML_USERNAME", "admin"))
    parser.add_argument("--phase", choices=["import", "functional"], default="import")
    parser.add_argument("--console", choices=["ssh", "websocket"], default="ssh")
    parser.add_argument(
        "--ssh-host", help="CML console server host, if different from the HTTPS/API host"
    )
    parser.add_argument(
        "--known-hosts",
        type=Path,
        default=Path.home() / ".ssh/known_hosts",
        help="Previously verified CML console-server host keys; unknown or mismatched keys are rejected",
    )
    parser.add_argument(
        "--lab",
        default="",
        help="Substring of a lab path; functional checks use curated entries only",
    )
    parser.add_argument(
        "--image-override",
        action="append",
        default=[],
        metavar="TYPE=IMAGE_ID",
        help="Private image selection, e.g. iosv=iosv-159-3-m12; source YAML stays portable",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "private-validation/result.json")
    args = parser.parse_args()
    if urlsplit(args.url).scheme != "https":
        parser.error("Use HTTPS with a trusted certificate; TLS verification is never disabled")
    password = os.environ.get("CML_PASSWORD") or getpass.getpass("CML password: ")
    client = ClientLibrary(
        args.url, username=args.username, password=password, ssl_verify=True, timeout=60
    )
    overrides = {}
    available = (
        {x["id"]: x["node_definition_id"] for x in client.definitions.image_definitions()}
        if args.image_override
        else {}
    )
    for choice in args.image_override:
        kind, separator, image = choice.partition("=")
        if not separator or kind not in RAM_MIB or available.get(image) != kind:
            parser.error("Image override must select an installed image of the matching node type")
        overrides[kind] = image
    baseline = {
        l.id: (str(l.state()), topology_signature(yaml.safe_load(l.download())))
        for l in client.all_labs()
    }
    if args.phase == "functional" and any(
        state not in ("STOPPED", "DEFINED_ON_CORE") for state, _ in baseline.values()
    ):
        raise RuntimeError(
            "An existing lab is active. Stop it yourself or choose another test window."
        )
    checks = json.loads((ROOT / "validation/checks.json").read_text(encoding="utf-8"))
    paths = sorted((ROOT / "labs").rglob("*.yaml"))
    if args.lab:
        paths = [p for p in paths if args.lab in p.relative_to(ROOT).as_posix()]
    if args.phase == "functional":
        paths = [p for p in paths if p.relative_to(ROOT).as_posix() in checks]
    if not paths:
        raise ValueError("No matching lab paths")
    tag = "CML-Labs QA " + uuid.uuid4().hex[:10] + " - "
    results = []
    version = client.system_info()["version"]
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        data = load(path)
        errors = validate(data)
        if errors:
            raise ValueError("\n".join(errors))
        row = {
            "path": relative,
            "sha256": digest(path),
            "cml_version": version,
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "checks": [],
        }
        lab = None
        connections = {}
        failure = None
        try:
            if args.phase == "functional":
                if sum(n.get("ram") or RAM_MIB[n["node_definition"]] for n in data["nodes"]) > 4096:
                    raise ValueError(
                        "This small-lab harness refuses more than 4096 MiB nominal node RAM"
                    )
                if any(
                    str(l.state()) not in ("STOPPED", "DEFINED_ON_CORE") for l in client.all_labs()
                ):
                    raise RuntimeError("Another lab became active; no new test is started")
            data["lab"]["title"] = (tag + data["lab"]["title"])[:64]
            for node in data["nodes"]:
                if node["node_definition"] in overrides:
                    node["image_definition"] = overrides[node["node_definition"]]
            lab = client.import_lab(yaml.safe_dump(data, sort_keys=False))
            exported = yaml.safe_load(lab.download())
            assert len(exported["nodes"]) == len(data["nodes"]) and len(exported["links"]) == len(
                data["links"]
            )
            assert graph_signature(exported) == graph_signature(data)
            assert config_signature(exported["nodes"]) == config_signature(data["nodes"])
            if args.phase == "functional":
                plan = checks[relative]
                row["plan_sha256"] = plan_digest(plan)
                lab.start(wait=False)
                deadline = time.monotonic() + 720
                while time.monotonic() < deadline:
                    try:
                        states = running_node_states(lab.nodes())
                        ready = bool(states)
                    except (APIError, HTTPError):
                        ready = False
                    if ready:
                        break
                    time.sleep(8)
                else:
                    raise TimeoutError("Node boot/readiness timed out")
                row["startup_states"] = states
                row["images"] = {n.label: n.image_definition for n in lab.nodes()}
                row["image_selection"] = (
                    "explicit private overrides"
                    if overrides
                    else "controller defaults; null means the API did not expose the effective image"
                )
                row["console_transport"] = args.console
                row["client_versions"] = {
                    package: package_version(package)
                    for package in ("cryptography", "paramiko", "virl2-client", "websockets")
                }

                def console(label, connections=connections, lab=lab):
                    if label not in connections:
                        node = lab.get_node_by_label(label)
                        connections[label] = (
                            SSHConsole(
                                client,
                                args.ssh_host or urlsplit(args.url).hostname,
                                node,
                                lab,
                                args.known_hosts,
                            )
                            if args.console == "ssh"
                            else WebConsole(client, args.url, node)
                        )
                    return connections[label]

                row["console_boot_fallback"] = verify_unconfirmed_consoles(states, console)

                if plan.get("repair"):
                    execute_prerequisites(plan, console, row["checks"].append)
                    check = plan["checks"][0]
                    initial = console(check["node"]).command(check["command"])
                    assert check["command"] in initial and "% Invalid input" not in initial, (
                        "Initial console check was not executed"
                    )
                    ok = not bool(re.search(check["pattern"], initial, re.MULTILINE))
                    row["checks"].append(
                        {"name": "initial fault detected", "passed": ok, "output": initial[-3500:]}
                    )
                    assert ok, "Expected deliberate fault was absent"
                    for command in plan["repair"]["commands"]:
                        output = console(plan["repair"]["node"]).command(command, 5)
                        passed = command in output and not CLI_ERROR.search(output)
                        row["checks"].append(
                            {
                                "phase": "repair",
                                "kind": "configuration",
                                "node": plan["repair"]["node"],
                                "command": command,
                                "passed": bool(passed),
                                "output": output[-3500:],
                            }
                        )
                        assert passed, "Repair command failed: " + command
                    time.sleep(12)
                execute_plan(plan, console, row["checks"].append)
                row["status"] = "passed"
            else:
                row["status"] = "import-export-pass"
        except BaseException as exc:  # noqa: BLE001 - Record interruptions and clean up; re-raise below.
            failure = exc
            row["status"] = "failed"
            row["error"] = type(exc).__name__
            # Do not serialize transport exceptions that could contain deployment URLs or auth details.
        finally:
            for connection in connections.values():
                connection.close()
            if lab:
                lid = lab.id
                assert lid not in baseline and lab.title.startswith(tag), (
                    "Refusing cleanup outside this run"
                )
                if str(lab.state()) not in ("STOPPED", "DEFINED_ON_CORE"):
                    lab.stop(wait=False)
                    deadline = time.monotonic() + 90
                    while (
                        str(lab.state()) not in ("STOPPED", "DEFINED_ON_CORE")
                        and time.monotonic() < deadline
                    ):
                        time.sleep(2)
                if str(lab.state()) in ("STOPPED", "DEFINED_ON_CORE"):
                    lab.wipe(wait=True)
                    lab.remove()
                    row["test_lab_removed"] = True
                else:
                    row["test_lab_removed"] = False
                    row["status"] = "failed"
                    row["test_lab_id"] = lid
                    failure = RuntimeError(
                        "Test lab did not stop. Inspect your CML instance; no forced stop was attempted."
                    )
            row["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            results.append(row)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "phase": args.phase,
                        "image_overrides": overrides,
                        "run_complete": False,
                        "labs": results,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            print(relative, row["status"], flush=True)
        if failure:
            raise RuntimeError("Test failed; inspect the private result file") from None
    current = {l.id: l for l in client.all_labs()}
    assert set(current) == set(baseline), "Lab inventory changed during the test window"
    assert all(
        str(current[lid].state()) == state
        and topology_signature(yaml.safe_load(current[lid].download())) == signature
        for lid, (state, signature) in baseline.items()
    ), "Existing-lab state/configuration changed"
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "phase": args.phase,
                "cml_version": version,
                "image_overrides": overrides,
                "run_complete": True,
                "original_lab_count": len(baseline),
                "original_labs_unchanged": True,
                "test_labs_remaining": 0,
                "labs": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("All original labs unchanged; no test lab remains.")


if __name__ == "__main__":
    main()
