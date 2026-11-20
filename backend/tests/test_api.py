"""Tests for the content_feed backend.

Run with:  python -m unittest discover -s backend/tests -v
"""

from __future__ import annotations

import contextlib
import io
import os
import sqlite3
import unittest

from backend.api import dispatch
from backend.db import Database, stamp
from backend.service import MAX_ATTEMPTS

CODE = "123456"


class BackendTests(unittest.TestCase):
    def setUp(self):
        self._old_code = os.environ.get("DEV_FIXED_CODE")
        os.environ["DEV_FIXED_CODE"] = CODE
        self.db = Database("sqlite:///:memory:")

    def tearDown(self):
        self.db.close()
        if self._old_code is None:
            os.environ.pop("DEV_FIXED_CODE", None)
        else:
            os.environ["DEV_FIXED_CODE"] = self._old_code

    def call(self, method, path, body=None, token=None):
        headers = {"authorization": f"Bearer {token}"} if token else {}
        return dispatch(method, path, body, headers, self.db)

    def sign_in(self, phone):
        self.call("POST", "/auth/request-code", {"phone": phone})
        status, payload = self.call("POST", "/auth/verify-code",
                                    {"phone": phone, "code": CODE})
        self.assertEqual(status, 200, payload)
        return payload["token"]

    def make_creator(self, phone, handle):
        token = self.sign_in(phone)
        status, payload = self.call("PUT", "/me/profile",
                                    {"handle": handle, "display_name": handle.title()},
                                    token)
        self.assertEqual(status, 200, payload)
        return token, payload["creator"]

    # -- health & routing -------------------------------------------------
    def test_health_and_unknown_endpoint(self):
        self.assertEqual(self.call("GET", "/health"),
                         (200, {"ok": True, "service": "content_feed"}))
        status, payload = self.call("GET", "/nope")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"]["code"], "not_found")

    # -- sign-in ----------------------------------------------------------
    def test_code_is_logged_and_expires_in_five_minutes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status, payload = self.call("POST", "/auth/request-code",
                                        {"phone": "+2348012345678"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["sent"])
        self.assertEqual(payload["expires_in"], 300)
        self.assertIn(CODE, out.getvalue())
        row = self.db.one("SELECT * FROM login_codes")
        self.assertIsNotNone(row)
        self.assertFalse(row["consumed"])

    def test_expired_code_is_rejected(self):
        phone = "+2348012345678"
        self.call("POST", "/auth/request-code", {"phone": phone})
        self.db.execute("UPDATE login_codes SET expires_at = ?", ("2000-01-01T00:00:00Z",))
        status, payload = self.call("POST", "/auth/verify-code",
                                    {"phone": phone, "code": CODE})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "code_expired")

    def test_wrong_code_counts_attempts_and_locks_after_five(self):
        phone = "+2348012345678"
        self.call("POST", "/auth/request-code", {"phone": phone})
        for expected_status in [400, 400, 400, 400, 429]:
            status, payload = self.call("POST", "/auth/verify-code",
                                        {"phone": phone, "code": "000000"})
            self.assertEqual(status, expected_status, payload)
        row = self.db.one("SELECT * FROM login_codes")
        self.assertEqual(row["attempts"], MAX_ATTEMPTS)
        self.assertTrue(row["consumed"])
        status, payload = self.call("POST", "/auth/verify-code",
                                    {"phone": phone, "code": CODE})
        self.assertEqual(status, 400)

    def test_successful_login_creates_user_and_session(self):
        phone = "+2348012345678"
        token = self.sign_in(phone)
        self.assertTrue(token)
        user = self.db.one("SELECT * FROM users WHERE phone = ?", (phone,))
        self.assertIsNotNone(user)
        status, payload = self.call("GET", "/me/profile", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(payload["user"]["phone"], phone)
        self.assertIsNone(payload["creator"])

    def test_code_cannot_be_used_twice_and_invalid_inputs(self):
        phone = "+2348012345678"
        self.sign_in(phone)
        status, payload = self.call("POST", "/auth/verify-code",
                                    {"phone": phone, "code": CODE})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "invalid_code")
        status, _ = self.call("POST", "/auth/request-code", {"phone": "123"})
        self.assertEqual(status, 400)

    # -- profiles ---------------------------------------------------------
    def test_unique_handles_enforced(self):
        self.make_creator("+2348010000001", "ada")
        token2 = self.sign_in("+2348010000002")
        status, payload = self.call("PUT", "/me/profile", {"handle": "ada"}, token2)
        self.assertEqual(status, 409)
        self.assertEqual(payload["error"]["code"], "handle_taken")

    def test_handle_validation_and_profile_update(self):
        token, creator = self.make_creator("+2348010000001", "ada")
        self.assertEqual(creator["handle"], "ada")
        self.assertEqual(creator["follower_count"], 0)
        for bad in ["ab", "A B", "has-dash"]:
            status, _ = self.call("PUT", "/me/profile", {"handle": bad}, token)
            self.assertEqual(status, 400)
        status, payload = self.call(
            "PUT", "/me/profile",
            {"bio": "Comedy sketches", "location": "Lagos", "display_name": "Ada O."},
            token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["creator"]["bio"], "Comedy sketches")
        self.assertEqual(payload["creator"]["location"], "Lagos")
        self.assertEqual(payload["creator"]["display_name"], "Ada O.")
        status, _ = self.call("PUT", "/me/profile", {"unknown": 1}, token)
        self.assertEqual(status, 400)

    def test_profile_requires_auth(self):
        status, payload = self.call("PUT", "/me/profile", {"handle": "ada"})
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "unauthorized")

    # -- creators & follows -----------------------------------------------
    def test_get_creator_public_profile(self):
        token, _ = self.make_creator("+2348010000001", "ada")
        status, payload = self.call("GET", "/creators/ada")
        self.assertEqual(status, 200)
        self.assertEqual(payload["handle"], "ada")
        self.assertNotIn("phone", payload)
        self.assertFalse(payload["following"])
        status, payload = self.call("GET", "/creators/ADA", token=token)
        self.assertEqual(status, 200)
        status, _ = self.call("GET", "/creators/nobody")
        self.assertEqual(status, 404)

    def test_follow_unfollow_and_counts(self):
        token, _ = self.make_creator("+2348010000001", "ada")
        fan = self.sign_in("+2348010000002")
        status, payload = self.call("POST", "/follow/ada", token=fan)
        self.assertEqual(status, 200)
        self.assertTrue(payload["following"])
        self.assertEqual(payload["follower_count"], 1)
        status, payload = self.call("POST", "/follow/ada", token=fan)
        self.assertEqual(status, 200)
        self.assertEqual(payload["follower_count"], 1)  # idempotent
        profile = self.call("GET", "/creators/ada", token=fan)[1]
        self.assertTrue(profile["following"])
        status, payload = self.call("DELETE", "/follow/ada", token=fan)
        self.assertEqual(status, 200)
        self.assertFalse(payload["following"])
        self.assertEqual(payload["follower_count"], 0)

    def test_cannot_follow_self_or_unknown(self):
        token, _ = self.make_creator("+2348010000001", "ada")
        status, payload = self.call("POST", "/follow/ada", token=token)
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "cannot_follow_self")
        fan = self.sign_in("+2348010000002")
        for method in ("POST", "DELETE"):
            status, payload = self.call(method, "/follow/nobody", token=fan)
            self.assertEqual(status, 404)
        status, _ = self.call("POST", "/follow/ada")
        self.assertEqual(status, 401)

    # -- data model -------------------------------------------------------
    def test_money_minor_units_and_fee_split(self):
        _, alice = self.make_creator("+2348010000001", "alice")
        fan = self.sign_in("+2348010000002")
        fan_id = self.db.one("SELECT id FROM users WHERE phone = ?",
                             ("+2348010000002",))["id"]
        self.db.execute(
            "INSERT INTO tips (from_user_id, to_creator_id, amount_minor, currency, "
            "platform_fee_minor, creator_amount_minor, created_at) "
            "VALUES (?, ?, 1000, 'NGN', 200, 800, ?)",
            (fan_id, alice["user_id"], stamp()),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO tips (from_user_id, to_creator_id, amount_minor, currency, "
                "platform_fee_minor, creator_amount_minor, created_at) "
                "VALUES (?, ?, 1000, 'NGN', 200, 700, ?)",
                (fan_id, alice["user_id"], stamp()),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO payouts (creator_id, amount_minor, currency, provider, "
                "destination, created_at) VALUES (?, -1, 'NGN', 'OPay', 'x', ?)",
                (alice["user_id"], stamp()),
            )


if __name__ == "__main__":
    unittest.main()
