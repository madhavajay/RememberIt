"""Tests for rememberit.client module."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


class TestCloseCollectionQuiet:
    """Tests for _close_collection_quiet to prevent recursion bugs."""

    def test_calls_col_close_not_itself(self) -> None:
        """Ensure _close_collection_quiet calls col.close(), not itself."""
        from rememberit.client import _close_collection_quiet

        mock_col = MagicMock()
        mock_col.close = MagicMock()

        _close_collection_quiet(mock_col)

        mock_col.close.assert_called_once()

    def test_no_infinite_recursion(self) -> None:
        """Ensure function completes without recursion error."""
        from rememberit.client import _close_collection_quiet

        mock_col = MagicMock()
        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(100)

        try:
            _close_collection_quiet(mock_col)
        except RecursionError:
            pytest.fail("_close_collection_quiet has infinite recursion!")
        finally:
            sys.setrecursionlimit(old_limit)

    def test_suppresses_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure stdout is suppressed during close."""
        from rememberit.client import _close_collection_quiet

        mock_col = MagicMock()
        mock_col.close = lambda: print("DEBUG: should not appear")

        _close_collection_quiet(mock_col)

        captured = capsys.readouterr()
        assert "DEBUG" not in captured.out


class TestGenerateSessionKey:
    """Tests for _generate_session_key."""

    def test_returns_8_char_string(self) -> None:
        from rememberit.client import _generate_session_key

        key = _generate_session_key()
        assert len(key) == 8
        assert key.isalnum()

    def test_randomness(self) -> None:
        from rememberit.client import _generate_session_key

        keys = {_generate_session_key() for _ in range(100)}
        assert len(keys) > 90


class TestSession:
    """Tests for Session dataclass."""

    def test_session_creation(self) -> None:
        from rememberit.client import Session

        sess = Session(hkey="abc123", endpoint="https://example.com")
        assert sess.hkey == "abc123"
        assert sess.endpoint == "https://example.com"
        assert sess.username is None
        assert sess.password is None

    def test_session_with_credentials(self) -> None:
        from rememberit.client import Session

        sess = Session(
            hkey="abc123",
            endpoint="https://example.com",
            username="user@test.com",
            password="secret",
        )
        assert sess.username == "user@test.com"
        assert sess.password == "secret"


class TestLoadSaveSession:
    """Tests for session persistence."""

    def test_load_session_missing_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import client

        monkeypatch.setattr(client, "SESSION_PATH", tmp_path / "nonexistent.json")

        result = client.load_session()
        assert result is None

    def test_save_and_load_session(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import client
        from rememberit.client import Session, load_session, save_session

        session_file = tmp_path / "config.json"
        monkeypatch.setattr(client, "SESSION_PATH", session_file)

        sess = Session(hkey="test123", endpoint="https://test.com", username="user")
        save_session(sess)

        loaded = load_session()
        assert loaded is not None
        assert loaded.hkey == "test123"
        assert loaded.endpoint == "https://test.com"
        assert loaded.username == "user"


class TestRememberItClient:
    """Tests for RememberItClient class."""

    def test_client_init_no_session(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import client
        from rememberit.client import RememberItClient

        monkeypatch.setattr(client, "SESSION_PATH", tmp_path / "nonexistent.json")

        c = RememberItClient()
        assert c.session is None

    def test_client_init_with_session(self) -> None:
        from rememberit.client import RememberItClient, Session

        sess = Session(hkey="abc", endpoint="https://test.com")
        c = RememberItClient(session=sess)
        assert c.session == sess

    def test_get_sync_key_no_session(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import client
        from rememberit.client import RememberItClient

        monkeypatch.setattr(client, "SESSION_PATH", tmp_path / "nonexistent.json")

        c = RememberItClient()
        assert c.get_sync_key() is None

    def test_get_sync_key_with_session(self) -> None:
        from rememberit.client import RememberItClient, Session

        sess = Session(hkey="mykey123", endpoint="https://test.com")
        c = RememberItClient(session=sess)
        assert c.get_sync_key() == "mykey123"

    def test_logout_clears_session(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import client
        from rememberit.client import RememberItClient, Session

        session_file = tmp_path / "config.json"
        session_file.write_text('{"hkey": "test", "endpoint": "https://test.com"}')
        monkeypatch.setattr(client, "SESSION_PATH", session_file)

        sess = Session(hkey="test", endpoint="https://test.com")
        c = RememberItClient(session=sess)
        c.logout()

        assert c.session is None
        assert not session_file.exists()


class TestRunInThread:
    """Tests for _run_in_thread helper."""

    def test_returns_result(self) -> None:
        from rememberit.client import _run_in_thread

        result = _run_in_thread(lambda: 42)
        assert result == 42

    def test_propagates_exception(self) -> None:
        from rememberit.client import _run_in_thread

        def raises():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            _run_in_thread(raises)
