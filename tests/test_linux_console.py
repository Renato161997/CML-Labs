import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from linux_console import establish_linux_shell


class NativeLinuxConsoleTest(unittest.TestCase):
    def run_bootstrap(self, uid_output, prompt_output=None, label="TOOLS"):
        outputs = iter(
            [
                uid_output,
                prompt_output or "root@container:/# export PS1='root@TOOLS:~# '\nroot@TOOLS:~# ",
            ]
        )
        sent = []
        establish_linux_shell(label, sent.append, lambda _: next(outputs))
        return sent

    def test_uid_is_checked_before_prompt_change(self):
        sent = self.run_bootstrap("root@container:/# id -u\n0\nroot@container:/# ")
        self.assertEqual(sent[0], "\rid -u\r")
        self.assertTrue(sent[1].startswith("\rexport PS1="))

    def test_busybox_prompt_can_be_framed(self):
        self.run_bootstrap("/ # id -u\n0\n/ # ")

    def test_root_looking_prompt_does_not_prove_uid_zero(self):
        with self.assertRaisesRegex(RuntimeError, "UID-zero"):
            self.run_bootstrap("root@container:/# id -u\n1000\nroot@container:/# ")

    def test_old_uid_before_echo_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "UID-zero"):
            self.run_bootstrap("0\nroot@container:/# id -u\n1000\nroot@container:/# ")

    def test_incomplete_or_corrupted_echo_is_rejected(self):
        for output in ("0\nroot@container:/# ", "root@container:/# id --u\n0\nroot@container:/# "):
            with self.subTest(output=output), self.assertRaisesRegex(RuntimeError, "echo"):
                self.run_bootstrap(output)

    def test_prompt_change_needs_expected_new_prompt(self):
        with self.assertRaisesRegex(RuntimeError, "prompt could not"):
            self.run_bootstrap(
                "root@container:/# id -u\n0\nroot@container:/# ",
                "root@container:/# export PS1='root@TOOLS:~# '\nroot@container:/# ",
            )

    def test_shell_metacharacters_in_label_rejected_without_sending(self):
        for label in ("TOOLS';id;#", "$(id)", "TOOLS\nreboot", "", None):
            sent = []
            with self.subTest(label=label), self.assertRaises(ValueError):
                establish_linux_shell(label, sent.append, lambda _: "")
            self.assertEqual(sent, [])
