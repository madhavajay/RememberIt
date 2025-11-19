from __future__ import annotations

from rememberit.config import Settings, config_path, load_settings, save_settings


def test_save_and_load_settings(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("REMEMBERIT_CONFIG_DIR", str(tmp_path))

    settings = Settings(
        email="me@example.com",
        password="topsecret",
        user_agent="UA/1.0",
        cookie_header="ankiweb=abc; has_auth=1",
        debug_log_path="/tmp/rememberit.log",
    )
    path = save_settings(settings)

    assert path == config_path()
    loaded = load_settings()
    assert loaded.email == settings.email
    assert loaded.password == settings.password
    assert loaded.user_agent == settings.user_agent
    assert loaded.cookie_header == settings.cookie_header
