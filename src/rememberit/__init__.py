from .client import (
    DEFAULT_USER_AGENT,
    DEFAULT_MODEL_ID,
    ANKIWEB_BASE_URL,
    RememberItClient,
    RememberItError,
    Deck,
)
from .config import Settings, config_path, load_settings, save_settings
from .formatting import decks_markdown_table
from .proto import DeckNode
from .models import DeckListResult, CardSummary, DeckCollection, Card, CardCollection

__version__ = "0.1.3"

_client = RememberItClient()


def login(email: str, password: str, *, persist: bool = True) -> dict:
    return _client.login(email, password, persist=persist)


def sync():
    """Trigger a full sync (decks + cards) and return a DeckCollection."""
    return _client.sync()


def decks():
    """Return cached decks (auto-sync if empty)."""
    return _client.decks()


def delete_deck(deck: Deck | str | int):
    """Delete a deck by object, name/path, or id."""
    return _client.remove_deck(deck)


def rename_deck(deck: Deck | str | int, new_name: str):
    """Rename a deck by object, name/path, or id."""
    return _client.rename_deck(deck, new_name)


def load_deck(
    path: str | dict,
    *,
    deck_name: str | None = None,
    model_id: int = DEFAULT_MODEL_ID,
    replace: bool = False,
):
    """Import a JSON deck file or mapping and upsert cards into the target deck; returns Deck."""
    return _client.load_deck(path, deck_name=deck_name, model_id=model_id, replace=replace)


def upload_deck(
    path: str | dict,
    *,
    deck_name: str | None = None,
    model_id: int = DEFAULT_MODEL_ID,
    replace: bool = False,
):
    """Alias for load_deck for API symmetry (path can be str or dict)."""
    return load_deck(path, deck_name=deck_name, model_id=model_id, replace=replace)


def create_deck(name: str):
    """Create a deck via /svc/decks/create-deck and return it after sync."""
    return _client.create_deck(name)


def docs() -> str:
    """
    Return an AI-friendly Markdown cheatsheet for RememberIt usage and deck JSON format.
    """
    text = """# RememberIt AI Cheatsheet

## JSON Deck Format (for AI editing)
```json
{
  "name": "Example Deck",
  "deck_id": 123456789,
  "model_id": 1763445109221,
  "cards": [
    {"note_id": 987654321, "front": "Question?", "back": "Answer", "tags": "tag1 tag2"},
    {"front": "New Q", "back": "New A", "tags": ""}
  ]
}
```
- `note_id` optional: if present we update; if missing we add.
- `tags` optional string (space-separated); currently stored but not round-tripped from search responses.

## Import / Upsert
- `rememberit.load_deck(deck_json_or_path, deck_name=None, replace=False, model_id=1763445109221)`
  - Accepts a Python dict or a JSON file path.
  - Resolves deck by `deck_id` or `name` (or override with `deck_name`); auto-syncs once.
  - If deck not found and `name` is provided, auto-creates it via /svc/decks/create-deck.
  - For each card: update if `note_id` given; else if (front/back) already exist, skip; else add.
  - `replace=True` forces updates when the same note_id/front exists but content differs.
  - Deduplicates cards within the payload by (front, back).
  - Syncs and returns the Deck.
- Alias: `rememberit.upload_deck(...)`.
"""
    print(text)
    return text


def set_debug_log(path: str | None, *, persist: bool = True) -> None:
    _client.set_debug_log(path, persist=persist)


def set_cookie_header(cookie_header: str, *, persist: bool = True) -> None:
    """Manually set cookies for authenticated calls (e.g. pasted from browser)."""
    _client.set_cookie_header(cookie_header, persist=persist)


def set_cookie_header_ankiweb(cookie_header: str, *, persist: bool = True) -> None:
    _client.set_cookie_header_ankiweb(cookie_header, persist=persist)


def set_cookie_header_ankiuser(cookie_header: str, *, persist: bool = True) -> None:
    _client.set_cookie_header_ankiuser(cookie_header, persist=persist)


def help() -> str:  # noqa: A001
    """Show available commands."""
    commands = {
        "login(email, password, persist=True)": "Log in (if/when working) and save creds",
        "sync()": "Sync decks and cards (returns DeckCollection)",
        "decks()": "Return cached decks (auto-sync if empty)",
        "delete_deck(deck)": "Delete a deck by object, name/path, or id",
        "rename_deck(deck, new_name)": "Rename a deck by object, name/path, or id",
        "load_deck(path, deck_name=None, model_id=DEFAULT_MODEL_ID, replace=False)": "Import JSON/dict and upsert cards",
        "upload_deck(path, deck_name=None, model_id=DEFAULT_MODEL_ID, replace=False)": "Alias for load_deck",
        "create_deck(name)": "Create a deck via /svc/decks/create-deck",
        "sync_host_key(email, password)": "Legacy sync login to retrieve sync key (k)",
        "docs()": "Print AI-friendly usage and JSON schema",
        "set_cookie_header(cookie_header, persist=True)": "Paste browser cookie for auth (legacy single host)",
        "set_cookie_header_ankiweb(cookie_header, persist=True)": "Paste cookie for ankiweb.net calls",
        "set_cookie_header_ankiuser(cookie_header, persist=True)": "Paste cookie for ankiuser.net calls",
        "set_debug_log(path, persist=True)": "Write request/response logs to a file",
    }
    lines = ["RememberIt commands:"]
    for cmd, desc in commands.items():
        lines.append(f"  rememberit.{cmd} - {desc}")
    msg = "\n".join(lines)
    print(msg)
    return msg


__all__ = [
    "__version__",
    "login",
    "sync",
    "decks",
    "delete_deck",
    "rename_deck",
    "load_deck",
    "upload_deck",
    "create_deck",
    "sync_host_key",
    "docs",
    "set_cookie_header_ankiweb",
    "set_cookie_header_ankiuser",
    "set_debug_log",
    "set_cookie_header",
    "DEFAULT_USER_AGENT",
    "DEFAULT_MODEL_ID",
    "ANKIWEB_BASE_URL",
    "RememberItClient",
    "RememberItError",
    "Deck",
    "DeckCollection",
    "Card",
    "CardCollection",
    "DeckNode",
    "DeckListResult",
    "CardSummary",
    "Settings",
    "config_path",
    "load_settings",
    "save_settings",
    "decks_markdown_table",
    "help",
]


# Show help message when module is imported in a notebook
try:
    __IPYTHON__  # type: ignore
    print("RememberIt loaded! Try:")
    print("  rememberit.help()")
    print('  rememberit.set_cookie_header("ankiweb=...; has_auth=1")')
    print("  rememberit.sync()")
    print("  rememberit.decks()  # list decks, then deck[0] or deck['name'] to inspect")
except NameError:
    # Not in IPython/Jupyter, skip the message
    pass
