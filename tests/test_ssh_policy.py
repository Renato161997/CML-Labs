import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "examples/management"))
from ssh_policy_probe import assess


class SSHPolicyTests(unittest.TestCase):
    def test_transport_denial_does_not_accept_bad_password_or_host_identity(self):
        self.assertTrue(all(assess("denied", 255, "Connection closed by remote host").values()))
        for output in (
            "Permission denied",
            "Connection closed\nAuthentication failed",
            "REMOTE HOST IDENTIFICATION HAS CHANGED",
            "Host key verification failed",
            "Connection closed\nCurrent privilege level is 1",
            "Connection closed\nR1>",
        ):
            with self.subTest(output=output):
                self.assertFalse(all(assess("denied", 255, output).values()))

    def test_successful_session_cannot_be_labelled_source_policy_denial(self):
        self.assertFalse(all(assess("denied", 0, "Connection closed").values()))

    def test_elevated_privilege_requires_actual_configuration_mode(self):
        self.assertTrue(
            all(assess("elevated", 0, "Current privilege level is 15\nR1(config)#end").values())
        )
        for code, output in (
            (0, "Current privilege level is 15\nR1#"),
            (0, "Current privilege level is 1\nR1>"),
            (255, "Current privilege level is 15\nR1(config)#end"),
        ):
            self.assertFalse(all(assess("elevated", code, output).values()))
