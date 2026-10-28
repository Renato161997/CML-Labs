"""Reconcile one real route from an explicitly approved immutable local Git revision."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

import requests
from api_probe import connect_verified, connection_options, hostname, rest
from route_probe import GOOD, observed_next_hops, route_config

REPO = Path("/lab/gitops-repo")
APPROVAL = Path("/lab/gitops-approved.json")
PRESENT = {"device": "API", "prefix": "192.0.2.42/32", "next_hop": GOOD, "state": "present"}


def git(*arguments):
    environment = dict(
        os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0"
    )
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(REPO), *arguments],
        env=environment,
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    return result.stdout.strip()


def validate(intent):
    if not isinstance(intent, dict) or set(intent) != set(PRESENT):
        raise ValueError("Unexpected intent fields")
    if any(intent[key] != PRESENT[key] for key in ("device", "prefix", "next_hop")):
        raise ValueError("Intent exceeds the isolated allowlist")
    if intent["state"] not in ("present", "absent"):
        raise ValueError("Invalid desired route state")
    return intent


def commit(intent, message):
    (REPO / "intent.json").write_text(json.dumps(intent, sort_keys=True) + "\n")
    git("add", "--", "intent.json")
    git("commit", "--no-gpg-sign", "-m", message)
    return git("rev-parse", "HEAD")


def initialize():
    if not REPO.exists():
        REPO.mkdir()
        git("init", "--initial-branch=main")
        (REPO / ".git/info/exclude").write_text("/.cml-fixture\n")
        git("config", "--local", "user.name", "CML Lab")
        git("config", "--local", "user.email", "cml-lab@example.test")
        revision = commit(PRESENT, "Approved training route intent")
        (REPO / ".cml-fixture").write_text("owned-offline-gitops-fixture-v1")
        # Simulated review decision, intentionally outside the untrusted repository.
        APPROVAL.write_text(json.dumps({"revision": revision}))
    assert (REPO / ".cml-fixture").read_text() == "owned-offline-gitops-fixture-v1"
    assert not git("remote"), "This exercise never contacts an external Git server"
    assert git("ls-files").splitlines() == ["intent.json"]


def approved_revision():
    revision = json.loads(APPROVAL.read_text())["revision"]
    assert re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", revision)
    return revision


def intent_at(revision):
    if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", revision):
        raise ValueError("An immutable commit ID is required")
    return validate(json.loads(git("show", revision + ":intent.json")))


def deploy(revision):
    if revision != approved_revision():
        raise PermissionError("Revision has no out-of-band fixture approval")
    desired = intent_at(revision)
    with connect_verified(connection_options()) as session:
        before = observed_next_hops(session)
        assert before in ([], [GOOD]) and hostname(session) == "API"
        expected = [GOOD] if desired["state"] == "present" else []
        if before != expected:
            payload = route_config("replace", GOOD) if expected else route_config("delete")
            assert session.edit_config(target="running", config=payload).ok
        assert observed_next_hops(session) == expected
        assert hostname(session) == "API"
    return before != expected


def run(mode):
    with requests.Session() as http:
        http.trust_env = False
        assert rest(http).status_code == 200
    initialize()
    revision = approved_revision()
    assert git("rev-parse", "main") == revision
    if mode == "drift":
        with connect_verified(connection_options()) as session:
            assert observed_next_hops(session) == [] and hostname(session) == "API"
        assert intent_at(revision)["state"] == "present"
        return {
            "status": "passed",
            "mode": mode,
            "approved_revision": revision,
            "real_device_drift": True,
            "device_writes": 0,
        }
    if mode == "guards":
        with connect_verified(connection_options()) as session:
            assert observed_next_hops(session) == [GOOD]
        git("checkout", "-b", "unreviewed-" + os.urandom(4).hex())
        unreviewed = commit(dict(PRESENT, state="absent"), "Unreviewed proposal")
        try:
            try:
                deploy(unreviewed)
            except PermissionError:
                pass
            else:
                raise AssertionError("An unreviewed revision reached deployment")
            bad = commit(dict(PRESENT, prefix="0.0.0.0/0"), "Forbidden route proposal")
            try:
                intent_at(bad)
            except ValueError:
                pass
            else:
                raise AssertionError("An out-of-scope default route passed policy")
            with connect_verified(connection_options()) as session:
                assert observed_next_hops(session) == [GOOD] and hostname(session) == "API"
        finally:
            git("checkout", "main")
        assert git("rev-parse", "main") == revision and not git("status", "--porcelain")
        return {
            "status": "passed",
            "mode": mode,
            "approved_revision": revision,
            "unreviewed_commit_rejected": True,
            "forbidden_intent_rejected": True,
            "actual_route_unchanged": True,
        }
    changed = deploy(revision)
    assert deploy(revision) is False, "Reconciliation must be state-idempotent"
    return {
        "status": "passed",
        "mode": mode,
        "approved_revision": revision,
        "real_git_commit": True,
        "real_netconf_reconciliation": True,
        "changed": changed,
        "repeat_changed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("baseline", "reconcile", "drift", "guards"))
    print(json.dumps(run(parser.parse_args().mode), sort_keys=True))
