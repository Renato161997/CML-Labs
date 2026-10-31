"""Accounting must pair actual viewer start/stop records by session ID."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT_BASH = Path("C:/Program Files/Git/usr/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
if not BASH and shutil.which("git"):
    bundled = Path(shutil.which("git")).parent.parent / "usr/bin/sh.exe"
    if bundled.exists():
        BASH = str(bundled)


@unittest.skipUnless(BASH, "Bash is required for the native accounting fixture")
class AccountingTests(unittest.TestCase):
    def parse(self, backend, text, passed, count=0):
        result = subprocess.run(
            [
                BASH,
                "-c",
                'source "$1"; "$2"',
                "bash",
                (ROOT / "examples/management/aaa_accounting.sh").as_posix(),
                backend + "_records",
            ],
            input=text,
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
        self.assertEqual(result.returncode, 0 if passed else 1, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["passed"], passed)
        self.assertEqual(evidence["completed_sessions"], count)

    @staticmethod
    def radius(status, identifier="00000005", user="viewer"):
        return (
            f'\tUser-Name = "{user}"\n\tAcct-Status-Type = {status}\n'
            f'\tAcct-Session-Id = "{identifier}"\n\n'
        )

    def test_radius_actual_pair(self):
        self.parse("radius", self.radius("Start") + self.radius("Stop"), True, 1)

    def test_radius_start_alone(self):
        self.parse("radius", self.radius("Start"), False)

    def test_radius_different_sessions(self):
        self.parse("radius", self.radius("Start") + self.radius("Stop", "other"), False)

    def test_radius_wrong_user(self):
        self.parse("radius", self.radius("Start", user="admin") + self.radius("Stop"), False)

    def test_radius_duplicate_records_not_extra_sessions(self):
        self.parse("radius", (self.radius("Start") + self.radius("Stop")) * 2, True, 1)

    def test_radius_missing_session_id(self):
        text = '\tUser-Name = "viewer"\n\tAcct-Status-Type = Start\n\n'
        self.parse("radius", text + text.replace("Start", "Stop"), False)

    def test_tacacs_actual_pair(self):
        self.parse(
            "tacacs",
            "Oct 31 NAS tty1 viewer remote start task_id=22 service=shell\n"
            "Oct 31 NAS tty1 viewer remote stop task_id=22 service=shell\n",
            True,
            1,
        )

    def test_tacacs_different_sessions(self):
        self.parse("tacacs", "viewer start task_id=22\nviewer stop task_id=23\n", False)

    def test_tacacs_missing_user_and_stop(self):
        self.parse("tacacs", "viewer start task_id=22\nadmin stop task_id=22\n", False)

    def test_tacacs_missing_identifier(self):
        self.parse("tacacs", "viewer start\nviewer stop\n", False)

    def test_tacacs_untrusted_identifier_is_data(self):
        self.parse("tacacs", "viewer start task_id=$(false)\nviewer stop task_id=$(false)\n", False)

    def test_empty_logs_do_not_pass(self):
        for backend in ("radius", "tacacs"):
            self.parse(backend, "", False)
