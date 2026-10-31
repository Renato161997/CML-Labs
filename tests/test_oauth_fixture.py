import concurrent.futures
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

spec = importlib.util.spec_from_file_location(
    "oauth", Path(__file__).parents[1] / "examples/api-core/oauth_fixture.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.store = m.Store(":memory:")
        self.server = m.Server(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = m.Client("http://127.0.0.1:" + str(self.server.server_port))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.store.db.close()

    def test_rfc7636_vector_and_reject_malformed_verifiers(self):
        self.assertEqual(
            m.challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"),
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
        )
        for v in ["short", "A" * 129, "!" * 43, None]:
            with self.assertRaises(ValueError):
                m.challenge(v)

    def test_actual_code_flow_negative_controls_and_no_secret_output(self):
        result = m.probe(self.client.base, "code")
        self.assertEqual(result["status"], "passed")
        self.assertNotIn("access_token", json.dumps(result))

    def test_actual_expiry_rotation_replay_and_revocation(self):
        self.assertEqual(m.probe(self.client.base, "refresh")["status"], "passed")

    def test_concurrent_redemption_has_one_winner_and_replay_closes_family(self):
        location, state, verifier = self.client.authorization()
        code = self.client.callback(location, state)
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            replies = list(executor.map(lambda _: self.client.redeem(code, verifier), range(2)))
        self.assertEqual(sorted(r[0] for r in replies), [200, 400])
        issued = next(r[2] for r in replies if r[0] == 200)
        self.assertEqual(self.client.request("/resource", token=issued["access_token"])[0], 401)

    def test_bad_redirect_does_not_redirect_or_issue_code(self):
        _, _, v = self.client.authorization()
        from urllib.parse import urlencode

        q = {
            "client_id": m.CLIENT,
            "redirect_uri": m.CALLBACK + "/evil",
            "response_type": "code",
            "code_challenge_method": "S256",
            "code_challenge": m.challenge(v),
            "state": "s" * 24,
            "scope": m.SCOPE,
            "decision": "allow",
        }
        count = self.store.db.execute("SELECT count(*) FROM codes").fetchone()[0]
        status, headers, _ = self.client.request("/authorize?" + urlencode(q))
        self.assertEqual(status, 400)
        self.assertNotIn("Location", headers)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM codes").fetchone()[0], count)

    def test_duplicate_parameters_and_unicode_state_are_rejected(self):
        self.assertEqual(self.client.request("/authorize?client_id=a&client_id=b")[0], 400)
        location, state, _ = self.client.authorization()
        with self.assertRaises(ValueError):
            self.client.callback(location, state + "è")

    def test_expired_authorization_code_cannot_issue_tokens(self):
        location, state, verifier = self.client.authorization()
        code = self.client.callback(location, state)
        with self.store.lock, self.store.db:
            self.store.db.execute("UPDATE codes SET expires=0")
        self.assertEqual(self.client.redeem(code, verifier)[0], 400)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM tokens").fetchone()[0], 0)

    def test_client_rejects_nonisolated_targets_before_network_access(self):
        for base in [
            "https://127.0.0.1",
            "http://8.8.8.8",
            "http://user:example@127.0.0.1",
            "http://127.0.0.1/path",
            "http://localhost",
        ]:
            with self.assertRaises(ValueError):
                m.Client(base)

    def test_server_rejects_nonisolated_bind_before_listening(self):
        for host in ["0.0.0.0", "8.8.8.8", "::1"]:
            with self.assertRaises(ValueError):
                m.Server((host, 0), self.store)

    def test_hashed_token_state_survives_actual_sqlite_file_reopen(self):
        import secrets

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oauth.sqlite"
            s = m.Store(path)
            verifier = secrets.token_urlsafe(32)
            p = {
                "client_id": m.CLIENT,
                "redirect_uri": m.CALLBACK,
                "response_type": "code",
                "code_challenge_method": "S256",
                "code_challenge": m.challenge(verifier),
                "state": "s" * 24,
                "scope": m.SCOPE,
                "decision": "allow",
            }
            status, redirect = s.issue_code(p)
            self.assertEqual(status, 302)
            code = parse_qs(urlsplit(redirect["location"]).query)["code"][0]
            status, pair = s.exchange(
                {
                    "client_id": m.CLIENT,
                    "redirect_uri": m.CALLBACK,
                    "grant_type": "authorization_code",
                    "code_verifier": verifier,
                    "code": code,
                }
            )
            self.assertEqual(status, 200)
            s.db.close()
            reopened = m.Store(path)
            try:
                self.assertEqual(reopened.resource(pair["access_token"])[0], 200)
            finally:
                reopened.db.close()
            for secret in [code, pair["access_token"], pair["refresh_token"]]:
                self.assertNotIn(secret.encode(), path.read_bytes())

    def test_controlled_pkce_fault_and_actual_recovery(self):
        self.assertEqual(self.client.request("/control", {"mode": "weak-pkce"})[0], 403)
        self.assertEqual(
            self.client.request("/control", {"mode": "weak-pkce"}, control=True)[0], 200
        )
        self.assertTrue(m.probe(self.client.base, "code", "fault")["vulnerability_observed"])
        self.client.request("/control", {"mode": "healthy"}, control=True)
        self.assertEqual(m.probe(self.client.base, "code", "recovered")["status"], "passed")

    def test_controlled_refresh_reuse_fault_and_actual_recovery(self):
        self.client.request("/control", {"mode": "reusable-refresh"}, control=True)
        self.assertTrue(m.probe(self.client.base, "refresh", "fault")["vulnerability_observed"])
        self.client.request("/control", {"mode": "healthy"}, control=True)
        self.assertEqual(m.probe(self.client.base, "refresh", "recovered")["status"], "passed")

    def test_database_contains_hashes_not_issued_opaque_tokens(self):
        issued = self.client.login()
        with self.store.lock:
            dump = "\n".join(self.store.db.iterdump())
        for value in [issued["access_token"], issued["refresh_token"]]:
            self.assertNotIn(value, dump)
            self.assertIn(m.digest(value), dump)


if __name__ == "__main__":
    unittest.main()
