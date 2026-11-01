"""Disposable wired EAP-TLS peers and kernel locked-port admission fixture."""

import argparse
import http.client
import http.server
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path("/lab")
PROC = Path("/proc")
MARKER = "CML-WIRED-NAC-V1"
PID_OWNER_UID = 0
MAC = "02:00:00:00:00:10"
DOMAINS = {"AUTH": "auth.cml-lab.example", "CLIENT": "client.cml-lab.example"}
IPS = {"AUTH": "198.18.99.1", "CLIENT": "198.18.99.2"}


def run(args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
    if check and result.returncode:
        raise RuntimeError("Fixture command failed: " + args[0])
    return result


def role():
    value = (ROOT / "nac-role").read_text().strip()
    if value not in ("AUTH", "CLIENT"):
        raise ValueError("Unknown fixed role")
    return value


def write(path, text, mode=0o600):
    if path.is_symlink():
        raise ValueError("Fixture links refused")
    path.write_text(text)
    path.chmod(mode)


def certificates(who):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, DOMAINS[who])])
    now = datetime.now(UTC)
    eku = ExtendedKeyUsageOID.SERVER_AUTH if who == "AUTH" else ExtendedKeyUsageOID.CLIENT_AUTH
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(DOMAINS[who])]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([eku]), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    write(
        ROOT / "identity.key",
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
    )
    write(ROOT / "identity.pem", cert.public_bytes(serialization.Encoding.PEM).decode(), 0o644)


def accept_certificate(raw, expected):
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    cert = x509.load_pem_x509_certificate(raw)
    if not isinstance(cert.public_key(), rsa.RSAPublicKey) or cert.public_key().key_size < 2048:
        raise ValueError("Wrong fixture key type")
    cert.public_key().verify(
        cert.signature,
        cert.tbs_certificate_bytes,
        padding.PKCS1v15(),
        cert.signature_hash_algorithm,
    )
    if not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
        raise ValueError("Expected the explicit self-signed peer trust anchor")
    names = cert.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value.get_values_for_type(x509.DNSName)
    now = datetime.now(UTC)
    if (
        names != [DOMAINS[expected]]
        or not cert.not_valid_before_utc <= now < cert.not_valid_after_utc
    ):
        raise ValueError("Wrong peer fixture identity or lifetime")
    return cert


def hostapd_config():
    return (
        "driver=wired\ninterface=eth1\nieee8021x=1\nuse_pae_group_addr=1\neap_server=1\n"
        "ctrl_interface=/lab/hostapd\neap_user_file=/lab/eap.users\n"
        "ca_cert=/lab/peer.pem\nserver_cert=/lab/identity.pem\nprivate_key=/lab/identity.key\n"
    )


def supplicant_config(bad=False):
    domain = "wrong.cml-lab.example" if bad else DOMAINS["AUTH"]
    return (
        'ctrl_interface=/lab/wpa\nap_scan=0\nnetwork={\n key_mgmt=IEEE8021X\n eapol_flags=0\n phase1="allow_canned_success=0"\n eap=TLS\n identity="lab-client"\n'
        ' ca_cert="/lab/peer.pem"\n client_cert="/lab/identity.pem"\n private_key="/lab/identity.key"\n'
        ' domain_match="' + domain + '"\n}\n'
    )


def owned_pid(name):
    path = ROOT / (name + ".pid")
    if not path.exists():
        return None
    if path.is_symlink() or path.stat().st_uid != PID_OWNER_UID or path.stat().st_nlink != 1:
        raise ValueError("Unsafe PID metadata")
    pid = int(path.read_text())
    assert pid > 1
    for _ in range(3):
        try:
            stat = (PROC / str(pid) / "stat").read_text()
            if stat.split(") ", 1)[1].startswith("Z"):
                return None
            raw = (PROC / str(pid) / "cmdline").read_bytes()
        except (FileNotFoundError, ProcessLookupError):
            return None
        if raw:
            break
        # Linux may clear argv between the state read and zombie transition.
        # Never accept an empty identity as owned: recheck, then fail closed.
        time.sleep(0.02)
    else:
        raise ValueError("Owned process has no verifiable command identity")
    args = raw.split(b"\0")
    expected = {"auth": b"/lab/hostapd.conf", "supp": b"/lab/wpa.conf"}
    if name in expected:
        assert expected[name] in args and Path(args[0].decode()).name == (
            "hostapd" if name == "auth" else "wpa_supplicant"
        )
    else:
        assert b"/lab/n.py" in args and name.encode() in args
    return pid


def spawn(name, args):
    if owned_pid(name) is not None:
        raise ValueError("Owned fixture process already running")
    with (ROOT / (name + ".log")).open("wb") as log:
        process = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    write(ROOT / (name + ".pid"), str(process.pid))
    return process.pid


def stop(name):
    pid = owned_pid(name)
    if pid is not None:
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 4
        while owned_pid(name) is not None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert owned_pid(name) is None, "Owned process did not stop gracefully"
    return pid


def peer_certificate():
    other = "CLIENT" if role() == "AUTH" else "AUTH"
    conn = http.client.HTTPConnection(IPS[other], 8082, timeout=2)
    try:
        conn.request("GET", "/public.pem")
        response = conn.getresponse()
        raw = response.read(8193)
        if response.status != 200 or not 1 <= len(raw) <= 8192:
            raise ValueError("Unusable fixture certificate response")
        accept_certificate(raw, other)
        return raw
    finally:
        conn.close()


def public_server():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/public.pem":
                self.send_error(404)
                return
            raw = (ROOT / "identity.pem").read_bytes()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    http.server.HTTPServer((IPS[role()], 8082), Handler).serve_forever()


def authenticated():
    value = run(["hostapd_cli", "-p", "/lab/hostapd", "-i", "eth1", "sta", MAC], check=False)
    return value.returncode == 0 and any(
        line.startswith("flags=") and "[AUTHORIZED]" in line for line in value.stdout.splitlines()
    )


def admitted():
    entries = json.loads(run(["bridge", "-j", "fdb", "show", "br", "br0"]).stdout)
    return any(
        e.get("mac", "").lower() == MAC
        and e.get("ifname", e.get("dev")) == "eth1"
        and e.get("locked", False) is False
        and "locked" not in (e.get("flags") or [])
        for e in entries
    )


def locked():
    rows = json.loads(run(["bridge", "-j", "-d", "link", "show", "dev", "eth1"]).stdout)
    return len(rows) == 1 and rows[0].get("locked") is True and rows[0].get("learning") is False


def gate():
    assert role() == "AUTH"
    while True:
        policy = (ROOT / "admission-policy").read_text().strip()
        assert policy in ("strict", "mac")
        accepted = authenticated() if policy == "strict" else True
        assert locked(), "Kernel port lock changed unexpectedly"
        if accepted:
            run(["bridge", "fdb", "replace", MAC, "dev", "eth1", "master", "dynamic"])
        elif admitted():
            run(["bridge", "fdb", "del", MAC, "dev", "eth1", "master"])
        time.sleep(0.25)


def initialize():
    deadline = time.monotonic() + 90
    while True:
        try:
            raw = peer_certificate()
            break
        except (OSError, ValueError, http.client.HTTPException):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    write(ROOT / "peer.pem", raw.decode(), 0o644)
    if role() == "AUTH":
        write(ROOT / "eap.users", '"lab-client" TLS\n')
        write(ROOT / "hostapd.conf", hostapd_config())
        spawn("auth", ["hostapd", "-dd", "/lab/hostapd.conf"])
        spawn("gate", [sys.executable, "/lab/n.py", "gate"])
    else:
        write(ROOT / "wpa.conf", supplicant_config())
        spawn("supp", ["wpa_supplicant", "-D", "wired", "-i", "eth1", "-c", "/lab/wpa.conf", "-dd"])
    write(ROOT / "init-ready", "yes")


def configure():
    who = role()
    if who == "AUTH":
        run(
            [
                "ip",
                "link",
                "add",
                "br0",
                "type",
                "bridge",
                "ageing_time",
                "300",
                "no_linklocal_learn",
                "1",
            ]
        )
        for nic in ("eth1", "eth2"):
            run(["ip", "link", "set", nic, "master", "br0"])
            run(["ip", "link", "set", nic, "up"])
        run(["ip", "link", "set", "br0", "up"])
        run(["bridge", "link", "set", "dev", "eth1", "locked", "on", "learning", "off"])
        run(["ip", "route", "add", "unreachable", "198.18.10.0/24"])
        nic = "eth3"
        write(ROOT / "admission-policy", "strict")
    else:
        run(["ip", "link", "set", "eth1", "down"])
        run(["ip", "link", "set", "eth1", "address", MAC])
        run(["ip", "addr", "add", "198.18.10.10/24", "dev", "eth1"])
        run(["ip", "link", "set", "eth1", "up"])
        nic = "eth2"
    run(["ip", "addr", "add", IPS[who] + "/30", "dev", nic])
    run(["ip", "link", "set", nic, "up"])
    certificates(who)
    spawn("public", [sys.executable, "/lab/n.py", "public"])
    spawn("initialize", [sys.executable, "/lab/n.py", "initialize"])
    return {"status": "passed", "configured": who}


def client_status():
    result = run(["wpa_cli", "-p", "/lab/wpa", "-i", "eth1", "status"], check=False)
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    return (
        result.returncode == 0
        and values.get("wpa_state") == "COMPLETED"
        and values.get("EAP state") == "SUCCESS"
    )


def packets(source=False):
    options = ["-I", "198.18.10.10"] if source else []
    result = run(["ping", "-n", "-c", "3", "-W", "1", *options, "198.18.10.20"], check=False)
    match = re.search(r"3 packets transmitted, ([0-3]) received", result.stdout)
    if not match:
        raise ValueError("Incomplete independent ping output")
    return int(match[1])


def client_probe(phase):
    peer_certificate()  # Separate bootstrap/control path stays healthy.
    deadline = time.monotonic() + 45
    while True:
        auth = client_status()
        log = (
            (ROOT / "supp.log").read_text(errors="replace") if (ROOT / "supp.log").exists() else ""
        )
        mismatch = (
            "CTRL-EVENT-EAP-TLS-CERT-ERROR" in log
            and re.search(r"domain.{0,60}mismatch|mismatch.{0,60}domain", log, re.IGNORECASE)
            is not None
        )
        expected_auth = phase in ("client-good", "client-gate-expired")
        if auth == expected_auth and (expected_auth or mismatch):
            count = packets()
            expected = 3 if phase in ("client-good", "client-mac") else 0
            if count == expected:
                return {
                    "status": "passed",
                    "phase": phase,
                    "actual_eap_success": auth,
                    "domain_mismatch_observed": bool(mismatch),
                    "received": count,
                    "bootstrap_certificate_available": True,
                }
        if time.monotonic() >= deadline:
            raise AssertionError(
                "Actual EAP status and packet observations did not reach the required state"
            )
        time.sleep(1)


def recovered_data():
    deadline = time.monotonic() + 15
    consecutive = 0
    while True:
        count = packets()
        if time.monotonic() > deadline:
            raise AssertionError("Authorized data did not stabilize within the recovery window")
        consecutive = consecutive + 1 if count == 3 else 0
        if consecutive == 2:
            return
        time.sleep(0.25)


def control_no_bypass():
    assert client_status()
    peer_certificate()
    run(["ip", "route", "add", "198.18.10.20/32", "via", "198.18.99.1", "dev", "eth2"])
    try:
        assert packets(source=True) == 0, "The public-certificate path became a data bypass"
    finally:
        run(["ip", "route", "del", "198.18.10.20/32", "via", "198.18.99.1", "dev", "eth2"])
    recovered_data()
    return {
        "status": "passed",
        "phase": "control-no-bypass",
        "actual_management_path_blocked": True,
        "normal_data_recovered": True,
        "consecutive_recovery_samples": 2,
        "received_per_recovery_sample": 3,
    }


def control_isolated():
    routes = json.loads(run(["ip", "-j", "route", "show", "exact", "198.18.10.0/24"]).stdout)
    return any(
        row.get("type") == "unreachable" and row.get("dst") == "198.18.10.0/24" for row in routes
    )


def auth_probe(phase):
    assert control_isolated(), "The kernel control-path isolation route changed"
    deadline = time.monotonic() + 20
    while True:
        auth = authenticated()
        entry = admitted()
        policy = (ROOT / "admission-policy").read_text().strip()
        alive = owned_pid("gate") is not None
        assert locked()
        if phase == "auth-good":
            ok = auth and entry and alive and policy == "strict"
        elif phase == "auth-bad":
            ok = not auth and not entry and alive and policy == "strict"
        elif phase == "auth-mac":
            ok = not auth and entry and alive and policy == "mac"
        else:
            ok = (
                phase == "auth-gate-expired"
                and auth
                and not entry
                and not alive
                and policy == "strict"
            )
        if ok:
            return {
                "status": "passed",
                "phase": phase,
                "actual_peer_authorized": auth,
                "actual_fdb_admission": entry,
                "gate_alive": alive,
                "kernel_locked": True,
                "policy": policy,
            }
        if time.monotonic() >= deadline:
            raise AssertionError(
                "Actual authenticator and kernel admission did not reach the required state"
            )
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "configure",
            "public",
            "initialize",
            "gate",
            "control-no-bypass",
            "client-good",
            "client-bad",
            "client-mac",
            "client-gate-expired",
            "auth-good",
            "auth-bad",
            "auth-mac",
            "auth-gate-expired",
            "bad-domain",
            "good-domain",
            "strict",
            "mac",
            "gate-off",
            "gate-on",
        ),
    )
    action = parser.parse_args().action
    if os.geteuid() != 0 or (ROOT / "CML-NAC-FIXTURE").read_text().strip() != MARKER:
        raise PermissionError("Only the marked disposable NAC fixture is accepted")
    if action == "configure":
        result = configure()
    elif action == "public":
        public_server()
        return
    elif action == "initialize":
        initialize()
        return
    elif action == "gate":
        gate()
        return
    elif action == "control-no-bypass":
        assert role() == "CLIENT"
        result = control_no_bypass()
    elif action.startswith("client-"):
        assert role() == "CLIENT"
        result = client_probe(action)
    elif action.startswith("auth-"):
        assert role() == "AUTH"
        result = auth_probe(action)
    elif action in ("bad-domain", "good-domain"):
        assert role() == "CLIENT"
        run(["wpa_cli", "-p", "/lab/wpa", "-i", "eth1", "logoff"])
        stop("supp")
        write(ROOT / "wpa.conf", supplicant_config(action == "bad-domain"))
        spawn("supp", ["wpa_supplicant", "-D", "wired", "-i", "eth1", "-c", "/lab/wpa.conf", "-dd"])
        result = {"status": "passed", "domain_fault": action == "bad-domain"}
    elif action in ("strict", "mac"):
        assert role() == "AUTH"
        write(ROOT / "admission-policy", action)
        result = {"status": "passed", "policy": action}
    elif action == "gate-off":
        assert role() == "AUTH"
        pid = stop("gate")
        assert pid is not None
        write(ROOT / "old-gate.pid", str(pid))
        result = {"status": "passed", "gate_stopped": True}
    else:
        assert role() == "AUTH"
        old = int((ROOT / "old-gate.pid").read_text())
        pid = spawn("gate", [sys.executable, "/lab/n.py", "gate"])
        assert pid != old
        result = {"status": "passed", "gate_restarted": True}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
