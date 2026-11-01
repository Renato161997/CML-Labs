import importlib.util
import stat
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "secret_files", Path(__file__).resolve().parents[1] / "examples/security/secret_files.py"
)
secrets_lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secrets_lab)
KEY = "a" * 32


class SecretFileContracts(unittest.TestCase):
    def directory(self, **overrides):
        return SimpleNamespace(**({"st_mode": stat.S_IFDIR | 0o755, "st_uid": 0} | overrides))

    def file(self, **overrides):
        return SimpleNamespace(
            **(
                {"st_mode": stat.S_IFREG | 0o440, "st_uid": 0, "st_gid": 1500, "st_nlink": 1}
                | overrides
            )
        )

    def test_process_metadata_detects_a_real_key_without_returning_it(self):
        self.assertFalse(secrets_lab.process_exposure(KEY, b"python3 server.py", b"LANG=C"))
        for argv, environment in [
            (KEY.encode(), b"LANG=C"),
            (b"python3 server.py", b"TOKEN=" + KEY.encode()),
        ]:
            self.assertTrue(secrets_lab.process_exposure(KEY, argv, environment))

    def test_process_metadata_does_not_accept_invalid_key_or_textual_metadata(self):
        for key, argv, environment in [("bad", b"x", b"y"), (KEY, "x", b"y"), (KEY, b"x", "y")]:
            with self.assertRaises(AssertionError):
                secrets_lab.process_exposure(key, argv, environment)

    def test_key_format_is_closed(self):
        self.assertTrue(secrets_lab.valid_key(KEY))
        for value in [None, b"a" * 32, "a" * 31, "a" * 33, "A" * 32, "a" * 31 + "\n", "z" * 32]:
            with self.subTest(value=value):
                self.assertFalse(secrets_lab.valid_key(value))

    def test_only_exact_canonical_bearer_authenticates(self):
        self.assertTrue(secrets_lab.allowed("Bearer " + KEY, KEY))
        for header in [
            None,
            "",
            "Bearer " + KEY + "x",
            "Bearer " + "b" * 32,
            "Bearer " + KEY + "\r\n",
            "bearer " + KEY,
            "Bearer ÃƒÂ©",
            b"Bearer " + KEY.encode(),
        ]:
            with self.subTest(header=header):
                self.assertFalse(secrets_lab.allowed(header, KEY))

    def test_invalid_stored_key_never_authenticates(self):
        for value in [None, "", "invalid", "b" * 31]:
            self.assertFalse(secrets_lab.allowed("Bearer " + str(value), value))

    def test_rotation_invalidates_exact_prior_value(self):
        new = "b" * 32
        self.assertTrue(secrets_lab.allowed("Bearer " + KEY, KEY))
        self.assertFalse(secrets_lab.allowed("Bearer " + KEY, new))
        self.assertTrue(secrets_lab.allowed("Bearer " + new, new))

    def test_only_declared_private_and_fault_modes_are_accepted(self):
        for mode in [0o440, 0o444]:
            with patch.object(
                Path,
                "lstat",
                side_effect=[self.directory(), self.file(st_mode=stat.S_IFREG | mode)],
            ):
                self.assertEqual(secrets_lab.keypath().name, "runtime.key")

    def test_key_symlink_hardlink_wrong_owner_or_mode_is_refused(self):
        for change in [
            {"st_mode": stat.S_IFLNK | 0o440},
            {"st_mode": stat.S_IFREG | 0o644},
            {"st_nlink": 2},
            {"st_uid": 1501},
            {"st_uid": 1500},
            {"st_gid": 1501},
        ]:
            with (
                self.subTest(change=change),
                patch.object(Path, "lstat", side_effect=[self.directory(), self.file(**change)]),
                self.assertRaises(AssertionError),
            ):
                secrets_lab.keypath()

    def test_parent_must_be_root_owned_traversable_and_not_writable_by_service(self):
        for change in [
            {"st_uid": 1500},
            {"st_mode": stat.S_IFDIR | 0o777},
            {"st_mode": stat.S_IFLNK | 0o755},
        ]:
            with (
                self.subTest(change=change),
                patch.object(Path, "lstat", return_value=self.directory(**change)),
                self.assertRaises(AssertionError),
            ):
                secrets_lab.folder()


if __name__ == "__main__":
    unittest.main()
