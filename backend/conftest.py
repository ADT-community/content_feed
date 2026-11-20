"""Shared test fixtures.

Living in backend/ (not backend/tests/) also puts backend/ on sys.path, so the
tests can `from app.main import app` without any packaging setup.
"""

import logging
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

OTP_LOGGER = "content_feed.auth"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client backed by its own empty SQLite file."""
    monkeypatch.setenv("FEED_DB", str(tmp_path / "test.db"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sms(caplog):
    """Stands in for a phone: reads codes out of the mocked SMS log."""
    caplog.set_level(logging.INFO, logger=OTP_LOGGER)

    class Inbox:
        @property
        def messages(self) -> list[str]:
            return [r.getMessage() for r in caplog.records if r.name == OTP_LOGGER]

        def last_code(self) -> str:
            codes = re.findall(r"code is (\d{6})", "\n".join(self.messages))
            assert codes, "no one-time code was logged"
            return codes[-1]

    return Inbox()


@pytest.fixture
def phone() -> str:
    return "+2348012345678"


@pytest.fixture
def request_code(client, sms):
    """Ask for a code and hand back what the user would have read on the phone."""

    def _request(number: str) -> str:
        response = client.post("/auth/otp", json={"phone": number})
        assert response.status_code == 200, response.text
        return sms.last_code()

    return _request
