from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_DIRNAME = ".rememberit"
DEFAULT_CONFIG_FILENAME = "settings.json"
ENV_CONFIG_DIR = "REMEMBERIT_CONFIG_DIR"


@dataclass
class Settings:
    email: str = ""
    password: str = ""
    sync_key: str = ""
    user_agent: str = ""
    cookie_header: str = ""
    cookie_header_ankiweb: str = ""
    cookie_header_ankiuser: str = ""
    debug_log_path: str = ""
    display_format: str = "table"


def _config_dir() -> Path:
    """Resolve the config directory, allowing override for tests via env."""
    override = os.getenv(ENV_CONFIG_DIR)
    return Path(override).expanduser() if override else Path.home() / DEFAULT_CONFIG_DIRNAME


def config_path() -> Path:
    return _config_dir() / DEFAULT_CONFIG_FILENAME


def load_settings(path: Path | None = None) -> Settings:
    target = path or config_path()
    if not target.exists():
        return Settings()

    with target.open("r", encoding="utf-8") as fh:
        try:
            raw: dict[str, Any] = json.load(fh)
        except json.JSONDecodeError:
            return Settings()

    return Settings(
        email=raw.get("email", ""),
        password=raw.get("password", ""),
        sync_key=raw.get("sync_key", ""),
        user_agent=raw.get("user_agent", ""),
        cookie_header=raw.get("cookie_header", ""),
        cookie_header_ankiweb=raw.get("cookie_header_ankiweb", ""),
        cookie_header_ankiuser=raw.get("cookie_header_ankiuser", ""),
        debug_log_path=raw.get("debug_log_path", ""),
        display_format=raw.get("display_format", "table"),
    )


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(settings)
    with target.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    try:
        target.chmod(0o600)
    except PermissionError:
        # Best-effort on platforms that support chmod
        pass
    return target
