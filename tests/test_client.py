from __future__ import annotations

import httpx

from rememberit.client import DEFAULT_USER_AGENT, RememberItClient
from rememberit.config import Settings, load_settings
from rememberit.proto import DeckListInfoResponse


def test_client_uses_pinned_user_agent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REMEMBERIT_CONFIG_DIR", str(tmp_path))
    ua = "RememberItTestUA/1.0"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["User-Agent"] == ua
        assert request.headers["Content-Type"] == "application/octet-stream"
        assert request.content == b"user@example.com pw"
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = RememberItClient(settings=Settings(user_agent=ua), transport=transport)

    resp = client.login(email="user@example.com", password="pw")

    assert resp["status_code"] == 200
    saved = load_settings()
    assert saved.user_agent == ua


def test_reset_user_agent(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REMEMBERIT_CONFIG_DIR", str(tmp_path))
    settings = Settings(user_agent="CustomUA/2.0")
    client = RememberItClient(settings=settings, transport=httpx.MockTransport(lambda req: httpx.Response(200)))

    reset_ua = client.reset_user_agent()

    assert reset_ua == DEFAULT_USER_AGENT
    saved = load_settings()
    assert saved.user_agent == DEFAULT_USER_AGENT


def test_set_cookie_header(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REMEMBERIT_CONFIG_DIR", str(tmp_path))
    cookie_header = "ankiweb=abc123; has_auth=1"

    def handler(request: httpx.Request) -> httpx.Response:
        # Cookie header should include what we set
        assert "ankiweb=abc123" in request.headers.get("Cookie", "")
        assert "has_auth=1" in request.headers.get("Cookie", "")
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = RememberItClient(settings=Settings(), transport=transport)
    client.set_cookie_header(cookie_header)

    resp = client.get_decks()
    assert resp == {"ok": True}


def test_get_decks_parses_proto(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REMEMBERIT_CONFIG_DIR", str(tmp_path))

    resp = DeckListInfoResponse()
    top = resp.top_node  # type: ignore[attr-defined]
    top.deck_id = 1
    top.name = "Default"
    resp.current_deck_id = 1
    payload = resp.SerializeToString()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/svc/decks/deck-list-info"
        return httpx.Response(200, content=payload)

    client = RememberItClient(settings=Settings(), transport=httpx.MockTransport(handler))
    decoded = client.get_decks()

    assert decoded["current_deck_id"] == 1
    assert decoded["top_node"].id == 1


def test_debug_log_writes(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REMEMBERIT_CONFIG_DIR", str(tmp_path))
    log_path = tmp_path / "log.jsonl"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = RememberItClient(settings=Settings(), transport=httpx.MockTransport(handler))
    client.set_debug_log(str(log_path), persist=False)
    client.get_decks = lambda: {"ok": True}  # type: ignore[assignment]
    client._request("GET", "/decks")  # type: ignore[arg-type]

    assert log_path.exists()
    assert log_path.read_text().strip() != ""
