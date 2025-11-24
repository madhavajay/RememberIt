from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .client import (
    RememberItClient,
    RememberItError,
    Session,
    add_demo,
    list_decks_and_cards,
    load_session,
)
from .config import Settings, config_path, load_settings, save_settings
from .models import (
    Card,
    CardCollection,
    CardSummary,
    Deck,
    DeckCollection,
    DeckListResult,
    OperationResult,
)

__version__ = "0.1.1"

_client = RememberItClient()


def login(
    email: str | None = None, password: str | None = None, *, endpoint: str | None = None
) -> OperationResult:
    """Authenticate with Anki sync and persist session."""
    _client.login(user=email, pw=password, endpoint=endpoint)
    return OperationResult("✓ Logged in successfully", 200)


def get_sync_key() -> str | None:
    return _client.get_sync_key()


def logout() -> None:
    _client.logout()
    print("✓ Logged out")


def sync() -> DeckCollection:
    """Sync down from AnkiWeb and return decks + cards."""
    return _client.sync()


def decks() -> DeckCollection:
    """Return cached decks (syncing down if empty)."""
    return _client.decks()


def create_deck(name: str) -> Deck:
    return _client.create_deck(name)


def delete_deck(deck: Deck | str | int) -> dict[str, Any]:
    return _client.remove_deck(deck)


def rename_deck(deck: Deck | str | int, new_name: str) -> dict[str, Any]:
    return _client.rename_deck(deck, new_name)


def upsert_deck(data: str | Mapping[str, Any], *, deck_name: str | None = None) -> Deck:
    """
    Create or update a deck with cards from a dict or JSON file.

    Schema: {"name": str, "cards": [{"front", "back", "note_id"?, "tags"?}]}
    Cards with matching 'front' text will be updated; new cards will be added.
    """
    if isinstance(data, Mapping):
        payload = dict(data)
    else:
        path = Path(data)
        payload = json.loads(path.read_text(encoding="utf-8"))

    cards = payload.get("cards")
    if not isinstance(cards, list):
        raise RememberItError("Deck JSON must include a 'cards' array")

    target_name = deck_name or payload.get("name")
    if not target_name:
        raise RememberItError("Deck name is required")

    try:
        deck_obj = decks()[target_name]
    except Exception:
        deck_obj = create_deck(target_name)

    existing_fronts = {c.front: c for c in deck_obj.cards}

    for card in cards:
        front = card.get("front", "")
        back = card.get("back", "")
        tags = card.get("tags", "")
        note_id = card.get("note_id")

        if note_id:
            _client.update_card(
                note_id=note_id, front=front, back=back, tags=tags, deck_id=deck_obj.id
            )
        elif front in existing_fronts:
            existing = existing_fronts[front]
            if existing.id is not None and (
                existing.back != back or (tags and tags != getattr(existing, "tags", ""))
            ):
                _client.update_card(
                    note_id=existing.id, front=front, back=back, tags=tags, deck_id=deck_obj.id
                )
        else:
            _client.add_card(deck_id=deck_obj.id, front=front, back=back, tags=tags)

    _client.sync_up()
    deck_obj.sync()
    return deck_obj


# Backwards compatibility alias
def load_deck(data: str | Mapping[str, Any], *, deck_name: str | None = None) -> Deck:
    return upsert_deck(data, deck_name=deck_name)


def llmtxt() -> None:
    """Display quickstart for LLM editing."""
    text = """# RememberIt - Anki-backed quickstart

```python
import rememberit

# rememberit.login("email@example.com", "password") # if you haven't logged in yet
decks = rememberit.sync()

# Add or update a deck in bulk
deck_data = {
    "name": "CLI Demo",
    "cards": [
        {"front": "Front 1", "back": "Back 1"},
        {"front": "Front 2", "back": "Back 2"},
    ]
}
rememberit.upsert_deck(deck_data)
```"""
    print(text)


def help() -> None:  # noqa: A001
    """Show available commands."""
    markdown = """# RememberIt API (Anki-backed)

| Function | Description |
|----------|-------------|
| `rememberit.login(email, password)` | Authenticate and save sync key |
| `rememberit.sync()` | Sync down and return decks |
| `rememberit.decks()` | Return cached decks |
| `rememberit.create_deck(name)` | Create a deck |
| `rememberit.delete_deck(deck)` | Delete by name/id/object |
| `rememberit.rename_deck(deck, new_name)` | Rename deck |
| `rememberit.upsert_deck(data)` | Add/update cards from dict/JSON |
| `rememberit.llmtxt()` | Show LLM-friendly quickstart guide |
"""
    print(markdown)


__all__ = [
    "__version__",
    "login",
    "logout",
    "get_sync_key",
    "sync",
    "decks",
    "create_deck",
    "delete_deck",
    "rename_deck",
    "upsert_deck",
    "load_deck",
    "add_demo",
    "list_decks_and_cards",
    "llmtxt",
    "help",
    "RememberItClient",
    "RememberItError",
    "DeckCollection",
    "Deck",
    "Card",
    "CardCollection",
    "DeckListResult",
    "CardSummary",
    "OperationResult",
    "Session",
    "load_session",
    "Settings",
    "config_path",
    "load_settings",
    "save_settings",
]
