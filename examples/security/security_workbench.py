"""Isolated loopback TLS, signed-indicator and API authorization teaching fixture.

Fresh training keys stay in the disposable guest. This is not a vendor controller,
STIX/TAXII service or production security platform. No external target is accepted.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import http.client
import http.server
import ipaddress
import json
import socket
import ssl
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

TOKENS = {"reader": "CML-READER-PUBLIC-FIXTURE", "admin": "CML-ADMIN-PUBLIC-FIXTURE"}


def now():
    return dt.datetime.now(dt.UTC)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    temporary = path.with_suffix(".next")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def private_key(path):
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def certificate(path):
    return x509.load_pem_x509_certificate(path.read_bytes())


def issue(root, name, ca_name=None, dns=None, ip=None, signer=False, expired=False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name + ".lab.example")])
    issuer = certificate(root / (ca_name + ".crt")).subject if ca_name else subject
    signing = private_key(root / (ca_name + ".key")) if ca_name else key
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now() - (dt.timedelta(days=2) if expired else dt.timedelta(minutes=5)))
        .not_valid_after(now() - dt.timedelta(days=1) if expired else now() + dt.timedelta(days=2))
        .add_extension(
            x509.BasicConstraints(ca=ca_name is None, path_length=0 if ca_name is None else None),
            critical=True,
        )
    )
    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False
    )
    builder = builder.add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(signing.public_key()), critical=False
    )
    builder = builder.add_extension(
        x509.KeyUsage(
            digital_signature=ca_name is not None,
            content_commitment=False,
            key_encipherment=ca_name is not None and not signer,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=ca_name is None,
            crl_sign=ca_name is None,
            encipher_only=None,
            decipher_only=None,
        ),
        critical=True,
    )
    if ca_name:
        builder = builder.add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.CODE_SIGNING if signer else ExtendedKeyUsageOID.SERVER_AUTH]
            ),
            critical=False,
        )
    names = ([x509.DNSName(dns)] if dns else []) + (
        [x509.IPAddress(ipaddress.ip_address(ip))] if ip else []
    )
    if names:
        builder = builder.add_extension(x509.SubjectAlternativeName(names), critical=False)
    cert = builder.sign(signing, hashes.SHA256())
    keyfile = root / (name + ".key")
    keyfile.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    keyfile.chmod(0o600)
    (root / (name + ".crt")).write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def initialize(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (root / "service.json").exists():
        raise ValueError("Fixture already initialized; preserve its existing training identity")
    issue(root, "root")
    issue(root, "unrelated")
    issue(root, "server", "root", dns="service.lab.example", ip="127.0.0.1")
    issue(root, "wrong-name", "root", dns="wrong.lab.example")
    issue(root, "untrusted", "unrelated", dns="service.lab.example")
    issue(root, "signer", "root", signer=True)
    issue(root, "expired", "root", dns="service.lab.example", expired=True)
    save_json(
        root / "client.json",
        {"trust": "root", "hostname": "service.lab.example", "token": "reader"},
    )
    save_json(
        root / "service.json",
        {
            "certificate": "server",
            "feed": "valid",
            "revision": 1,
            "admin_up": True,
            "issued_at": now().isoformat(),
        },
    )
    save_json(root / "seen.json", [])


class FixtureServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, root, port):
        self.root = root
        super().__init__(("127.0.0.1", port), FixtureHandler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        name = read_json(self.root / "service.json")["certificate"]
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(self.root / (name + ".crt"), self.root / (name + ".key"))
        try:
            return context.wrap_socket(connection, server_side=True), address
        except ssl.SSLError as exc:
            connection.close()
            raise OSError("TLS handshake rejected") from exc


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def reply(self, status, value):
        data = canonical(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def role(self):
        supplied = self.headers.get("Authorization", "")
        return next((role for role, token in TOKENS.items() if supplied == "Bearer " + token), None)

    def do_GET(self):
        state = read_json(self.server.root / "service.json")
        if self.path == "/health":
            return self.reply(
                200, {"service": "isolated-security-workbench", "revision": state["revision"]}
            )
        if not self.role():
            return self.reply(401, {"authorized": False})
        if self.path == "/api/inventory":
            return self.reply(
                200,
                {
                    "backend": "offline-fixture",
                    "interface": "Ethernet0/0",
                    "admin_up": state["admin_up"],
                },
            )
        if self.path == "/intelligence":
            issued = dt.datetime.fromisoformat(state["issued_at"])
            if state["feed"] == "expired":
                issued -= dt.timedelta(days=1)
            payload = {
                "id": "fixture-" + str(state["revision"]),
                "type": "ipv4-addr",
                "value": "192.0.2.99",
                "issued_at": issued.isoformat(),
                "expires_at": (issued + dt.timedelta(hours=1)).isoformat(),
            }
            signature = private_key(self.server.root / "signer.key").sign(
                canonical(payload), padding.PKCS1v15(), hashes.SHA256()
            )
            if state["feed"] == "tampered":
                payload["value"] = "192.0.2.100"
            return self.reply(
                200, {"payload": payload, "signature": base64.b64encode(signature).decode("ascii")}
            )
        self.reply(404, {"found": False})

    def do_PATCH(self):
        role = self.role()
        if role != "admin":
            return self.reply(403 if role else 401, {"authorized": False})
        if self.path != "/api/interface":
            return self.reply(404, {"found": False})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError("Invalid body length")
            body = json.loads(self.rfile.read(size))
            if (
                set(body) != {"name", "admin_up"}
                or body["name"] != "Ethernet0/0"
                or type(body["admin_up"]) is not bool
            ):
                raise ValueError("Invalid fixture intent")
        except (ValueError, TypeError):
            return self.reply(400, {"accepted": False})
        state = read_json(self.server.root / "service.json")
        state["admin_up"] = body["admin_up"]
        save_json(self.server.root / "service.json", state)
        self.reply(
            200, {"accepted": True, "backend": "offline-fixture", "admin_up": state["admin_up"]}
        )


def request(root, port, path, method="GET", body=None):
    config = read_json(root / "client.json")
    context = ssl.create_default_context(cafile=str(root / (config["trust"] + ".crt")))
    raw = socket.create_connection(("127.0.0.1", port), timeout=5)
    try:
        stream = context.wrap_socket(raw, server_hostname=config["hostname"])
    except BaseException:
        raw.close()
        raise
    negotiated_version = stream.version()
    connection = http.client.HTTPConnection(config["hostname"], port, timeout=5)
    connection.sock = stream
    try:
        headers = {"Authorization": "Bearer " + TOKENS.get(config["token"], "CML-INVALID-FIXTURE")}
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, canonical(body) if body is not None else None, headers)
        response = connection.getresponse()
        data = response.read(65537)
        if len(data) > 65536:
            raise ValueError("Oversized fixture response")
        return response.status, json.loads(data), negotiated_version
    finally:
        connection.close()


def configure(root, options):
    client = read_json(root / "client.json")
    state = read_json(root / "service.json")
    for key in ("trust", "hostname", "token"):
        if options.get(key) is not None:
            client[key] = options[key]
    changed = False
    for key in ("certificate", "feed"):
        if options.get(key) is not None:
            state[key] = options[key]
            changed = True
    if changed:
        state["revision"] += 1
        state["issued_at"] = now().isoformat()
    save_json(root / "client.json", client)
    save_json(root / "service.json", state)
    return {"configured": True, "revision": state["revision"]}


def probe(root, port, mode, operation="read"):
    try:
        path = (
            "/health" if mode == "tls" else "/intelligence" if mode == "intel" else "/api/inventory"
        )
        method, body = "GET", None
        if mode == "api" and operation != "read":
            path, method = "/api/interface", "PATCH"
            body = {"name": "Ethernet0/0", "admin_up": operation == "enable"}
            if operation == "invalid-boolean":
                body["admin_up"] = "false"
        status, value, version = request(root, port, path, method, body)
        result = {"verified": True, "tls": version, "status": status}
        if mode != "intel":
            return {**result, **value}
        if status != 200:
            return {**result, "accepted": False, "reason": "authorization"}
        signer = certificate(root / "signer.crt")
        root_cert = certificate(root / "root.crt")
        root_cert.public_key().verify(
            signer.signature,
            signer.tbs_certificate_bytes,
            padding.PKCS1v15(),
            signer.signature_hash_algorithm,
        )
        if (
            signer.issuer != root_cert.subject
            or ExtendedKeyUsageOID.CODE_SIGNING
            not in signer.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        ):
            raise ValueError("Untrusted signer identity")
        if not signer.not_valid_before_utc <= now() <= signer.not_valid_after_utc:
            raise ValueError("Signer certificate expired")
        payload = value["payload"]
        signer.public_key().verify(
            base64.b64decode(value["signature"], validate=True),
            canonical(payload),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        issued = dt.datetime.fromisoformat(payload["issued_at"])
        expiry = dt.datetime.fromisoformat(payload["expires_at"])
        if (
            issued.tzinfo is None
            or expiry.tzinfo is None
            or not issued <= now() < expiry
            or expiry - issued > dt.timedelta(days=1)
        ):
            return {**result, "accepted": False, "reason": "expired_or_invalid_time"}
        if (
            set(payload) != {"id", "type", "value", "issued_at", "expires_at"}
            or payload["type"] != "ipv4-addr"
            or ipaddress.ip_address(payload["value"]) not in ipaddress.ip_network("192.0.2.0/24")
        ):
            return {**result, "accepted": False, "reason": "fixture_schema"}
        seen = read_json(root / "seen.json")
        if payload["id"] in seen:
            return {**result, "accepted": False, "reason": "replay"}
        save_json(root / "seen.json", [*seen, payload["id"]])
        return {**result, "accepted": True, "id": payload["id"], "value": payload["value"]}
    except ssl.SSLCertVerificationError as exc:
        return {
            "verified": False,
            "reason": "hostname_mismatch"
            if exc.verify_code == 62
            else "certificate_expired"
            if exc.verify_code == 10
            else "certificate_not_trusted",
        }
    except InvalidSignature:
        return {"verified": True, "accepted": False, "reason": "invalid_signature"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "serve", "configure", "probe"))
    parser.add_argument("--root", type=Path, default=Path("/lab/security-workbench"))
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("-m", "--mode", choices=("tls", "api", "intel"), default="tls")
    parser.add_argument(
        "-o",
        "--operation",
        choices=("read", "disable", "enable", "invalid-boolean"),
        default="read",
    )
    parser.add_argument("--trust", choices=("root", "unrelated"))
    parser.add_argument("--hostname", choices=("service.lab.example", "wrong.lab.example"))
    parser.add_argument("--token", choices=("reader", "admin", "invalid"))
    parser.add_argument("--certificate", choices=("server", "wrong-name", "untrusted", "expired"))
    parser.add_argument("--feed", choices=("valid", "tampered", "expired"))
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose an unprivileged local fixture port")
    if args.action == "init":
        initialize(args.root)
        result = {"initialized": True}
    elif args.action == "serve":
        with FixtureServer(args.root, args.port) as server:
            server.serve_forever(poll_interval=0.1)
        return
    elif args.action == "configure":
        result = configure(args.root, vars(args))
    else:
        result = probe(args.root, args.port, args.mode, args.operation)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
