import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from linux_console import establish_ubuntu_shell

PROMPT = "root@DEVBOX:~# "
COMMAND = "cloud-init status --format json"


def status(value, errors=None):
    return COMMAND + "\n" + json.dumps({"status": value, "errors": errors or []}) + "\n" + PROMPT


def identity(uid=0):
    return [
        "id -u\n" + str(uid) + "\n" + PROMPT,
        "export PS1='root@DEVBOX:~# '\n" + PROMPT,
    ]


class UbuntuStartup(unittest.TestCase):
    def invoke(self, chunks):
        stream = iter(chunks)
        events = []

        def read(_):
            chunk = next(stream)
            events.append(("read", chunk))
            return chunk

        establish_ubuntu_shell("DEVBOX", PROMPT, lambda text: events.append(("send", text)), read)
        return events

    def test_root_prompt_alone_waits_for_cloud_final(self):
        events = self.invoke([status("running"), "", status("done"), *identity()])
        done = next(i for i, e in enumerate(events) if e == ("read", status("done")))
        uid = next(i for i, e in enumerate(events) if e == ("send", "\rid -u\r"))
        self.assertLess(done, uid)
        self.assertEqual(events.count(("send", "\r" + COMMAND + "\r")), 2)

    def test_getty_replacement_cannot_supply_a_complete_command_echo(self):
        interrupted = (
            "root@DEVBOX:~# cloud-init sta\n"
            "Cloud-init: Final Stage.\nDEVBOX login: root (automatic login)\n" + PROMPT
        )
        events = self.invoke([interrupted, "", status("done"), *identity()])
        self.assertEqual(events.count(("send", "\r" + COMMAND + "\r")), 2)
        self.assertEqual(events[-1], ("read", identity()[-1]))

    def test_boot_errors_stop_before_functional_commands(self):
        for payload in [
            status("error", ["runcmd failed"]),
            status("done", ["failed"]),
            status("disabled"),
        ]:
            with (
                self.subTest(payload=payload),
                self.assertRaisesRegex(RuntimeError, "successfully"),
            ):
                self.invoke([payload])

    def test_malformed_status_is_not_ready(self):
        with self.assertRaisesRegex(RuntimeError, "valid status"):
            self.invoke([COMMAND + "\nnot JSON\n" + PROMPT])

    def test_done_still_requires_actual_uid_zero(self):
        with self.assertRaisesRegex(RuntimeError, "UID-zero"):
            self.invoke([status("done"), *identity(1000)])

    def test_deadline_expires_without_trusting_a_prompt(self):
        with (
            patch("linux_console.time.monotonic", side_effect=[0, 241]),
            self.assertRaises(TimeoutError),
        ):
            establish_ubuntu_shell("DEVBOX", PROMPT, lambda _: None, lambda _: "")

    def test_timeout_and_label_are_bounded(self):
        for timeout in [True, 0, 601, "240"]:
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                establish_ubuntu_shell(
                    "DEVBOX", PROMPT, lambda _: None, lambda _: "", timeout=timeout
                )
        with self.assertRaises(ValueError):
            establish_ubuntu_shell("DEVBOX;id", PROMPT, lambda _: None, lambda _: "")


if __name__ == "__main__":
    unittest.main()
