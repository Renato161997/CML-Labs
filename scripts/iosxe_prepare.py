"""Bootstrap API trust only inside a newly imported disposable IOS XE lab.

No CML credential or private key enters the client. Public certificates and SSH
keys come from the authenticated CML serial console, not from network TOFU.
"""

import base64
import hashlib
import json
import re
import textwrap
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from acceptance import CLI_ERROR

OPERATION = "iosxe-api-v1"
FILES = {"/lab/peer-ca.pem", "/lab/peer-ssh.json"}


def implementation_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def select_certificate(output, now=None):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    now = now or datetime.now(UTC)
    candidates = {}
    for pem in re.findall(
        r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", output, re.DOTALL
    ):
        cert = x509.load_pem_x509_certificate(pem.encode())
        names = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        if len(names) != 1 or names[0].value != "api.cml-lab.example":
            continue
        try:
            sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        except x509.ExtensionNotFound as error:
            raise ValueError("API certificate is missing its explicit DNS SAN") from error
        if "api.cml-lab.example" not in sans.get_values_for_type(x509.DNSName):
            raise ValueError("API certificate is missing its explicit DNS SAN")
        if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
            raise ValueError("API certificate is not currently valid")
        if cert.signature_hash_algorithm.name != "sha256":
            raise ValueError("Expected a SHA-256-signed API certificate")
        candidates[cert.fingerprint(hashes.SHA256()).hex()] = pem + "\n"
    if len(candidates) != 1:
        raise ValueError("Expected exactly one unambiguous API certificate")
    return next(iter(candidates.values()))


def rsa_public_keys(output):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    keys = set()
    for block in re.split(r"Key name:", output)[1:]:
        if "Key Data:" not in block:
            continue
        words = []
        for line in block.split("Key Data:", 1)[1].splitlines():
            if re.fullmatch(r"\s*[0-9A-Fa-f]{2,}(?:\s+[0-9A-Fa-f]{2,})*\s*", line):
                words.extend(line.split())
        if not words or any(len(word) % 2 for word in words):
            raise ValueError("Malformed RSA public-key hex data")
        key = serialization.load_der_public_key(bytes.fromhex("".join(words)))
        if isinstance(key, rsa.RSAPublicKey) and key.key_size >= 2048:
            keys.add(
                key.public_bytes(
                    serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
                ).decode()
            )
    if not keys:
        raise ValueError("No adequate RSA public key was retrieved through serial")
    return keys


def match_scanned_key(output, trusted):
    keys = set(re.findall(r"(?m)^\[198\.18\.0\.1\]:830 (ssh-rsa [A-Za-z0-9+/=]+)\s*$", output))
    if len(keys) != 1 or not keys.issubset(trusted):
        raise ValueError("NETCONF host key does not match authenticated serial evidence")
    return next(iter(keys)).split()[1]


def upload_public_file(console, path, content):
    if path not in FILES:
        raise ValueError("Unexpected bootstrap output path")
    raw = content.encode()
    payload = "\n".join(textwrap.wrap(base64.b64encode(raw).decode(), 76))
    console.send_raw("\rbase64 -d > " + path + " <<'CML_PREPARE_EOF'\r")
    console.read(2)
    console.send_raw(payload.replace("\n", "\r") + "\rCML_PREPARE_EOF\r")
    console.read(10)
    output = console.command("sha256sum " + path)
    if hashlib.sha256(raw).hexdigest() not in output:
        raise ValueError("Public trust material transfer checksum failed")


def enroll_selfsigned(console):
    command = "crypto pki enroll LABTLS"
    console.send_raw("\r" + command + "\r")
    question = console.read(12)
    host = re.escape(console.label)
    echo = rf"(?m)^(?:{host}(?:\([^\n]*\))?#[ \t]*)?{re.escape(command)}[ \t]*$"
    if not re.search(echo, question) or not re.search(
        r"Generate Self Signed Router Certificate\?\s*\[yes/no\]", question
    ):
        raise ValueError("The expected certificate-enrollment dialogue was not established")
    console.send_raw("yes\r")
    answer = console.read(45, until_prompt=True)
    if "successfully created" not in answer.lower() or not re.search(
        rf"(?m)^{host}\(config\)#[ \t]*$", answer
    ):
        raise ValueError(
            "Certificate enrollment did not confirm success and a fresh configuration prompt"
        )
    # PKI logs can interleave the single-word answer echo. This tightly scoped
    # dialogue exception never changes ordinary command-completion matching.


def prepare_iosxe(router, client, record, *, now=None, sleep=time.sleep):
    def command(line, timeout=30):
        output = router.command(line, timeout)
        passed = not bool(CLI_ERROR.search(output))
        record(
            {
                "phase": "prepare",
                "kind": "configuration",
                "node": router.label,
                "command": line,
                "passed": passed,
                "output": output[-3500:],
            }
        )
        if not passed:
            raise ValueError("IOS XE bootstrap command failed")
        return output

    existing = command("show crypto key mypubkey rsa")
    if re.search(r"Key name:\s*LAB(?:SSH|TLS)(?:\s|$)", existing):
        raise ValueError("Refusing to replace an existing named lab key")
    now = (now or datetime.now(UTC)) - timedelta(minutes=5)
    month = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[
        now.month - 1
    ]
    command(
        f"clock set {now.hour:02d}:{now.minute:02d}:{now.second:02d} {now.day} {month} {now.year}"
    )
    command("debug crypto pki transactions")
    for line in (
        "configure terminal",
        "crypto key generate rsa general-keys label LABSSH modulus 3072",
        "crypto key generate rsa general-keys label LABTLS modulus 3072",
        "ip ssh rsa keypair-name LABSSH",
        "crypto pki trustpoint LABTLS",
        "enrollment selfsigned",
        "subject-name CN=api.cml-lab.example",
        "subject-alt-name api.cml-lab.example",
        "serial-number none",
        "fqdn api.cml-lab.example",
        "ip-address none",
        "revocation-check none",
        "rsakeypair LABTLS",
        "hash sha256",
        "exit",
    ):
        command(line, 60)
    enroll_selfsigned(router)
    for line in (
        "ip http secure-trustpoint LABTLS",
        "ip http secure-server",
        "restconf",
        "netconf-yang",
        "end",
    ):
        command(line, 60)
    deadline = time.monotonic() + 300
    while True:
        status = command("show platform software yang-management process")
        if re.search(r"confd\s*:\s*Running", status) and re.search(r"nginx\s*:\s*Running", status):
            break
        if time.monotonic() > deadline:
            raise TimeoutError("IOS XE API daemons did not become ready")
        sleep(10)
    command("undebug all")
    certificate = select_certificate(command("show crypto pki certificates pem"))
    trusted_keys = rsa_public_keys(command("show crypto key mypubkey rsa"))
    scan = client.command("ssh-keyscan -T 5 -p 830 -t rsa 198.18.0.1", 25)
    hostkey = match_scanned_key(scan, trusted_keys)
    upload_public_file(client, "/lab/peer-ca.pem", certificate)
    upload_public_file(
        client,
        "/lab/peer-ssh.json",
        json.dumps({"host": "198.18.0.1", "port": 830, "hostkey_b64": hostkey}) + "\n",
    )
