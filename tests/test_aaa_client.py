import importlib.util
import sys
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "examples/management"
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location("aaa_client", SOURCE / "aaa_client.py")
aaa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aaa)
sys.path.pop(0)


class AuthenticationDenial(unittest.TestCase):
    def test_actual_authentication_denied(self):
        self.assertTrue(aaa.rejected(255, "viewer: Permission denied (password)."))

    def test_network_failure_is_not_aaa_denial(self):
        for text in ("Connection timed out", "Connection refused", "Connection reset"):
            self.assertFalse(aaa.rejected(255, text))

    def test_host_identity_failure_is_not_aaa_denial(self):
        self.assertFalse(aaa.rejected(255, "HOST KEY VERIFICATION FAILED Permission denied"))

    def test_success_never_denied(self):
        self.assertFalse(aaa.rejected(0, "Permission denied"))
        self.assertFalse(aaa.rejected(255, "Current privilege level is 1 Permission denied"))
