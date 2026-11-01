"""Disposable OCI network-tool exercise: actual UID/capability and HTTP observations."""

import argparse
import ctypes
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path("/lab")
MARKER = "CML-CONTAINER-TOOL-V1"
UID = 65534
SENTINEL = b"PUBLIC CLASSROOM FILE-PERMISSION SENTINEL; NOT A CREDENTIAL\n"


def kernel_identity(text):
    rows = dict(line.split(":", 1) for line in text.splitlines() if ":" in line)
    uid = [int(x) for x in rows["Uid"].split()]
    gid = [int(x) for x in rows["Gid"].split()]
    groups = [int(x) for x in rows["Groups"].split()]
    caps = {name: int(rows[name].strip(), 16) for name in ("CapInh", "CapPrm", "CapEff", "CapAmb")}
    nnp = int(rows["NoNewPrivs"].strip())
    if len(uid) != 4 or len(gid) != 4 or nnp not in (0, 1):
        raise ValueError("Incomplete kernel identity")
    return {"uid": uid, "gid": gid, "groups": groups, "caps": caps, "no_new_privs": nnp}


def identity():
    return kernel_identity(Path("/proc/self/status").read_text())


def unprivileged(value):
    return (
        value["uid"] == [UID] * 4
        and value["gid"] == [UID] * 4
        and value["groups"] == []
        and all(count == 0 for count in value["caps"].values())
        and value["no_new_privs"] == 1
    )


def demote():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS, inherited through exec.
        raise OSError(ctypes.get_errno(), "Could not enable no-new-privileges")
    os.setgroups([])
    os.setgid(UID)
    os.setuid(UID)


def api_module():
    spec = importlib.util.spec_from_file_location("container_contract", ROOT / "a.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def workload(with_key=True):
    assert unprivileged(identity()), "Actual workload identity/capabilities did not drop"
    try:
        os.setuid(0)
    except PermissionError:
        pass
    else:
        raise AssertionError("Workload regained UID zero")
    assert unprivileged(identity())
    try:
        raw = (ROOT / "root-only.fixture").read_bytes()
    except PermissionError:
        readable = False
    else:
        assert raw == SENTINEL, "Unexpected fixture data; do not print it"
        readable = True
    result = api_module().verify(authenticated=with_key)
    scratch = ROOT / "u-work" / ("request-" + str(os.getpid()) + ".json")
    os.umask(0o077)
    record = {"uid": os.getuid(), "api_result": result}
    try:
        with scratch.open("x") as stream:
            json.dump(record, stream)
        metadata = scratch.lstat()
        assert stat.S_ISREG(metadata.st_mode) and metadata.st_uid == UID
        assert metadata.st_nlink == 1 and stat.S_IMODE(metadata.st_mode) == 0o600
        assert json.loads(scratch.read_text()) == record
    finally:
        if scratch.exists():
            scratch.unlink()
    return {
        "kernel_unprivileged": True,
        "root_regain_denied": True,
        "root_sentinel_readable": readable,
        "owned_result_written_and_removed": True,
        "pid": os.getpid(),
        "api": result,
    }


def setup():
    assert os.geteuid() == 0
    assert ROOT.is_dir() and not ROOT.is_symlink() and ROOT.lstat().st_uid == 0
    ROOT.chmod(0o755)
    for name in ("u.py", "a.py", "CML-CONTAINER-TOOL"):
        path = ROOT / name
        metadata = path.lstat()
        assert stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0 and metadata.st_nlink == 1
        path.chmod(0o644)  # Only deliberately public classroom code/marker.
    assert not (ROOT / "root-only.fixture").exists()
    with (ROOT / "root-only.fixture").open("xb") as stream:
        stream.write(SENTINEL)
    (ROOT / "root-only.fixture").chmod(0o600)
    work = ROOT / "u-work"
    work.mkdir(mode=0o700)
    os.chown(work, UID, UID)
    return {"status": "passed", "configured": True}


def verified(phase, result):
    if phase not in ("baseline", "readable", "no-key", "schema", "media"):
        raise ValueError("Unknown fixed evidence phase")
    for name in (
        "kernel_unprivileged",
        "root_regain_denied",
        "owned_result_written_and_removed",
    ):
        if result.get(name) is not True:
            raise AssertionError("Missing observed workload property: " + name)
    if result.get("root_sentinel_readable") is not (phase == "readable"):
        raise AssertionError("Actual filesystem permission outcome disagrees with phase")
    api = result["api"]
    if phase == "schema":
        assert api.get("accepted") is False and api.get("reason") == "schema_violation"
    elif phase == "media":
        assert api.get("accepted") is False and api.get("reason") == "unexpected_media"
    elif phase == "no-key":
        assert api.get("accepted") is True and api.get("wire_status") == 401
        assert api["body"] == {"error": "authentication_required"}
    else:
        assert api.get("accepted") is True and api.get("wire_status") == 200
        assert api["body"]["interface"] == {"name": "eth1", "carrier": True}
    return {
        "status": "passed",
        "phase": phase,
        **{k: v for k, v in result.items() if k != "api"},
    }


def probe(phase):
    assert os.geteuid() == 0 and Path("/.dockerenv").is_file()
    assert identity()["caps"]["CapEff"] & (1 << 21) == 0, "SYS_ADMIN is outside this fixture"
    metadata = (ROOT / "root-only.fixture").lstat()
    assert stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0 and metadata.st_nlink == 1
    assert (ROOT / "root-only.fixture").read_bytes() == SENTINEL
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "u.py"),
            "workload",
            "no-key" if phase == "no-key" else "key",
        ],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
        timeout=15,
        check=True,
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        preexec_fn=demote,
    )
    assert 1 <= len(process.stdout) <= 8192
    result = json.loads(process.stdout)
    assert type(result["pid"]) is int and result["pid"] > 1 and result["pid"] != os.getpid()
    return verified(phase, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "configure",
            "secure",
            "expose",
            "readable",
            "baseline",
            "schema",
            "media",
            "no-key",
            "workload",
        ),
    )
    parser.add_argument("key", nargs="?", choices=("key", "no-key"), default="key")
    args = parser.parse_args()
    assert (ROOT / "CML-CONTAINER-TOOL").read_text().strip() == MARKER
    if args.action == "workload":
        value = workload(args.key == "key")
    else:
        assert os.geteuid() == 0
        if args.action == "configure":
            value = setup()
        elif args.action in ("secure", "expose"):
            path = ROOT / "root-only.fixture"
            assert not path.is_symlink() and path.lstat().st_uid == 0
            path.chmod(0o600 if args.action == "secure" else 0o644)
            value = {"status": "passed", "root_file_readable": args.action == "expose"}
        else:
            value = probe(args.action)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
