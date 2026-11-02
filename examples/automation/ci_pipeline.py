"""Local Git-to-tested-ACL artifact pipeline; deployment is a separate device step."""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import policy_code as compiler

ROOT = Path("/lab")


class CandidateRejected(ValueError):
    pass


class StaleBuild(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("Duplicate intent field")
        out[key] = value
    return out


def decode(raw):
    if not 1 <= len(raw) <= 4096:
        raise ValueError("Bounded source required")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    compiler.compile_policy(value)
    return value


def git(*args):
    result = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT / "ci-repo"),
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgSign=false",
            *args,
        ],
        capture_output=True,
        timeout=10,
        check=True,
    )
    return result.stdout


def head():
    value = git("rev-parse", "HEAD").decode().strip()
    if not re.fullmatch("[0-9a-f]{40}", value):
        raise ValueError("Expected a local SHA1-format object identifier")
    return value


def source(revision):
    if not re.fullmatch("[0-9a-f]{40}", revision):
        raise ValueError("Literal object identifier required")
    tree = git("ls-tree", revision, "--", "intent.json").decode()
    if not re.fullmatch("100644 blob [0-9a-f]{40}\tintent.json\n", tree):
        raise ValueError("Only a regular committed intent is accepted")
    return git("show", revision + ":intent.json")


def save(path, value):
    assert not path.is_symlink()
    temp = path.with_suffix(".next")
    with temp.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True)
    temp.chmod(0o600)
    temp.replace(path)


def commit(value):
    target = ROOT / "ci-repo" / "intent.json"
    assert not target.is_symlink()
    target.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    git("add", "--", "intent.json")
    git("commit", "-m", "Classroom desired policy")
    return head()


def gate():
    """Run fixed tests in a distinct process against one committed snapshot."""
    raw = (ROOT / "ci-input.json").read_bytes()

    class Contract(unittest.TestCase):
        def test_candidate_is_within_scope(self):
            decode(raw)

        def test_candidate_compilation_is_deterministic(self):
            value = decode(raw)
            self.assertEqual(compiler.compile_policy(value), compiler.compile_policy(value))

        def test_candidate_preserves_admin_deny_and_control(self):
            text = compiler.compile_policy(decode(raw))
            self.assertIn("20 deny tcp any host 198.18.20.20 eq 9090\n", text)
            self.assertIn("30 permit icmp any any\n", text)

        def test_admin_allow_is_rejected(self):
            with self.assertRaises(ValueError):
                compiler.compile_policy(dict(compiler.intent(), administration="allow"))

        def test_wide_source_is_rejected(self):
            with self.assertRaises(ValueError):
                compiler.compile_policy(dict(compiler.intent(), source="0.0.0.0/0"))

        def test_boolean_version_is_rejected(self):
            with self.assertRaises(ValueError):
                compiler.compile_policy(dict(compiler.intent(), version=True))

        def test_extra_command_field_is_rejected(self):
            with self.assertRaises(ValueError):
                compiler.compile_policy(dict(compiler.intent(), commands=["permit ip any any"]))

        def test_duplicate_source_fields_are_rejected(self):
            with self.assertRaises(ValueError):
                decode(b'{"version":1,"version":2}')

    report = unittest.TextTestRunner(stream=io.StringIO()).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Contract)
    )
    value = {
        "passed": report.wasSuccessful(),
        "tests_run": report.testsRun,
        "errors": len(report.errors),
        "failures": len(report.failures),
    }
    print(json.dumps(value, sort_keys=True))
    return 0 if report.wasSuccessful() else 1


def build():
    if git("status", "--porcelain") != b"":
        raise ValueError("Dirty source cannot be built")
    revision = head()
    raw = source(revision)
    target = ROOT / "ci-input.json"
    assert not target.is_symlink()
    target.write_bytes(raw)
    target.chmod(0o600)
    run = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "gate"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    try:
        report = json.loads(run.stdout)
    except ValueError as exc:
        raise RuntimeError("Gate process did not return a valid report") from exc
    if run.returncode == 1 and report == {
        "passed": False,
        "tests_run": 8,
        "errors": 3,
        "failures": 0,
    }:
        try:
            decode(raw)
        except ValueError as exc:
            raise CandidateRejected(
                "The actual complete gate rejected the invalid candidate"
            ) from exc
        raise RuntimeError("Gate tests failed for an independently valid candidate")
    if run.returncode != 0 or report != {
        "passed": True,
        "tests_run": 8,
        "errors": 0,
        "failures": 0,
    }:
        raise RuntimeError("Gate process failed or returned an incomplete/unexpected result")
    value = decode(raw)
    body = compiler.compile_policy(value)
    bundle = {
        "commit": revision,
        "source_sha256": digest(raw),
        "intent": value,
        "body": body,
        "body_sha256": digest(body.encode()),
        "tests_run": 8,
    }
    save(ROOT / "ci-bundle.json", bundle)
    return {
        "status": "passed",
        "phase": "build",
        "commit": revision,
        "tests_run": 8,
        "application": value["application"],
        "published": False,
    }


def verify(bundle, current=True):
    if not isinstance(bundle, dict) or set(bundle) != {
        "commit",
        "source_sha256",
        "intent",
        "body",
        "body_sha256",
        "tests_run",
    }:
        raise ValueError("Invalid bundle envelope")
    if type(bundle["tests_run"]) is not int:
        raise ValueError("The fixed gate count must be an integer")
    raw = source(bundle["commit"])
    value = decode(raw)
    body = compiler.compile_policy(value)
    if bundle != {
        "commit": bundle["commit"],
        "source_sha256": digest(raw),
        "intent": value,
        "body": body,
        "body_sha256": digest(body.encode()),
        "tests_run": 8,
    }:
        raise ValueError("Bundle does not match its exact committed input")
    if current and (git("status", "--porcelain") != b"" or head() != bundle["commit"]):
        raise StaleBuild("Stale or dirty source cannot be promoted")
    return value


def promote(rollback=False):
    bundle = json.loads((ROOT / ("ci-rollback.json" if rollback else "ci-bundle.json")).read_text())
    value = verify(bundle, current=not rollback)
    if (
        not rollback
        and value["application"] == "allow"
        and not (ROOT / "ci-rollback.json").exists()
    ):
        save(ROOT / "ci-rollback.json", bundle)
    published = compiler.publish(value, ROOT / "approved.json")
    return {
        "status": "passed",
        "phase": "rollback" if rollback else "promote",
        "commit": bundle["commit"],
        "application": value["application"],
        "artifact_sha256": published["sha256"],
        "device_deployed": False,
    }


def rejected(action):
    before = {name: (ROOT / name).read_bytes() for name in ("ci-bundle.json", "approved.json")}
    try:
        action()
    except (CandidateRejected, StaleBuild):
        pass
    else:
        raise AssertionError("Unsafe or stale promotion was unexpectedly accepted")
    assert all((ROOT / name).read_bytes() == raw for name, raw in before.items())
    return {
        "status": "passed",
        "rejected": True,
        "bundle_unchanged": True,
        "publication_unchanged": True,
    }


def configure():
    (ROOT / "ci-repo").mkdir()
    git("init", "--initial-branch=main", "--object-format=sha1")
    git("config", "user.name", "CML Classroom")
    git("config", "user.email", "classroom@example.test")
    commit(compiler.intent(2, "allow"))
    compiler.publish(compiler.intent(1, "deny"), ROOT / "approved.json")
    with (ROOT / "policy-http.log").open("wb") as log:
        subprocess.Popen(
            [sys.executable, "/lab/p.py", "serve"],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return build()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "configure",
            "gate",
            "build",
            "promote",
            "deny-stale",
            "unsafe",
            "rollback",
            "restore",
        ),
    )
    action = parser.parse_args().action
    assert (
        os.geteuid() == 0 and (ROOT / "CML-CI-PIPELINE").read_text().strip() == "CML-CI-PIPELINE-V1"
    )
    if action == "gate":
        return gate()
    if action == "configure":
        value = configure()
    elif action == "build":
        value = build()
    elif action in ("promote", "rollback"):
        value = promote(rollback=action == "rollback")
    elif action == "deny-stale":
        commit(compiler.intent(3, "deny"))
        value = rejected(promote)
    elif action == "restore":
        commit(compiler.intent(5, "allow"))
        value = build()
    else:
        commit(dict(compiler.intent(4, "deny"), administration="allow"))
        value = rejected(build)
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
