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
from .models import DeckListResult, CardSummary, DeckCollection, Card, CardCollection, OperationResult

__version__ = "0.1.3"

_client = RememberItClient()


def login(email: str, password: str, *, persist: bool = True):
    """Authenticate with Anki and save sync key to ~/.rememberit/settings.json."""
    from .models import OperationResult

    key = _client.login(email, password, persist=persist)
    return OperationResult("✓ Logged in successfully", 200)


def get_sync_key() -> str | None:
    """Return cached sync key if available."""
    return _client.get_sync_key()


def logout() -> None:
    """Clear sync key and credentials (keeps settings file)."""
    _client.logout()
    print("✓ Logged out")


def reset() -> None:
    """Delete all RememberIt data from ~/.rememberit folder."""
    _client.reset()
    print("✓ Reset complete - all data deleted from ~/.rememberit")


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


def upsert_deck(
    data: str | dict,
    *,
    deck_name: str | None = None,
    model_id: int = DEFAULT_MODEL_ID,
    replace: bool = False,
):
    """Create or update a deck with cards from dict or JSON file. Returns Deck object."""
    return _client.load_deck(data, deck_name=deck_name, model_id=model_id, replace=replace)


# Backwards compatibility alias
def load_deck(
    path: str | dict,
    *,
    deck_name: str | None = None,
    model_id: int = DEFAULT_MODEL_ID,
    replace: bool = False,
):
    """Deprecated: Use upsert_deck() instead."""
    return upsert_deck(path, deck_name=deck_name, model_id=model_id, replace=replace)


def create_deck(name: str):
    """Create a deck via /svc/decks/create-deck and return it after sync."""
    return _client.create_deck(name)




def sync_meta_raw(sync_key: str, client_version: str | None = None) -> bytes:
    """Call /sync/meta and return decompressed raw bytes."""
    if client_version is None:
        client_version = "anki,25.09.2 (3890e12c),mac:15.5"
    return _client.sync_meta_raw(sync_key, client_version=client_version)


def sync_start_raw(sync_key: str, min_usn: int = 0, lnewer: bool = True, graves=None) -> bytes:
    """Call /sync/start and return decompressed raw bytes."""
    return _client.sync_start_raw(sync_key, min_usn=min_usn, lnewer=lnewer, graves=graves)


def llmtxt() -> None:
    """Show AI-friendly example for bulk deck operations."""
    from IPython.display import Markdown, display

    text = """# RememberIt - LLM Integration Guide

```python
import rememberit

# Create or update a deck with cards
deck_data = {
    "name": "Spanish Vocab",
    "cards": [
        {"front": "hello", "back": "hola"},
        {"front": "goodbye", "back": "adiós"}
    ]
}
deck = rememberit.upsert_deck(deck_data)

# Export deck as JSON string (easy to print/copy)
json_str = rememberit.decks()["Spanish Vocab"].json()
print(json_str)  # Pretty-printed JSON

# Or as dict for programmatic editing
deck_dict = rememberit.decks()["Spanish Vocab"].to_dict()
deck_dict["cards"].append({"front": "thank you", "back": "gracias"})
rememberit.upsert_deck(deck_dict)
```
"""

    try:
        # Try to display as Markdown in Jupyter
        from IPython import get_ipython
        if get_ipython() is not None:
            display(Markdown(text))
            return None  # Don't return string in Jupyter (prevents double display)
        else:
            print(text)
            return None
    except Exception:
        # Fallback if not in Jupyter
        print(text)
        return None

# Backwards compatibility alias
def docs() -> None:
    """Deprecated: Use llmtxt() instead."""
    llmtxt()


def set_debug_log(path: str | None, *, persist: bool = True) -> None:
    _client.set_debug_log(path, persist=persist)


def set_cookie_header(cookie_header: str, *, persist: bool = True) -> None:
    """Manually set cookies for authenticated calls (e.g. pasted from browser)."""
    _client.set_cookie_header(cookie_header, persist=persist)


def set_cookie_header_ankiweb(cookie_header: str, *, persist: bool = True) -> None:
    _client.set_cookie_header_ankiweb(cookie_header, persist=persist)


def set_cookie_header_ankiuser(cookie_header: str, *, persist: bool = True) -> None:
    _client.set_cookie_header_ankiuser(cookie_header, persist=persist)


def help() -> None:  # noqa: A001
    """Show available commands."""
    from IPython.display import Markdown, display

    markdown = """# RememberIt API Reference

## Authentication

| Function | Description |
|----------|-------------|
| `rememberit.login(email, password)` | Authenticate with AnkiWeb and save sync key |
| `rememberit.logout()` | Clear sync key and credentials |
| `rememberit.get_sync_key()` | Get current sync key |

## Deck Operations

| Function | Description |
|----------|-------------|
| `rememberit.sync()` | Download all decks and cards from server |
| `rememberit.decks()` | Get cached decks (call `sync()` to refresh) |
| `rememberit.create_deck(name)` | Create a new deck |
| `rememberit.delete_deck(deck)` | Delete a deck by name, ID, or object |
| `rememberit.rename_deck(deck, new_name)` | Rename a deck |

## Card Operations

| Function | Description |
|----------|-------------|
| `rememberit.upsert_deck(data, deck_name=None)` | Create or update deck with cards from dict/JSON |

## Utilities

| Function | Description |
|----------|-------------|
| `rememberit.llmtxt()` | Show AI integration examples |
| `rememberit.reset()` | Delete all RememberIt data from `~/.rememberit` |

---

**Quick Start:**
```python
# Login once
rememberit.login("email@example.com", "password")

# Create or update a deck with cards
deck_data = {
    "name": "My Deck",
    "cards": [
        {"front": "Question", "back": "Answer"},
    ]
}
deck = rememberit.upsert_deck(deck_data)

# View all decks
rememberit.decks()
```
"""

    try:
        # Try to display as Markdown in Jupyter
        from IPython import get_ipython
        if get_ipython() is not None:
            display(Markdown(markdown))
            return None  # Don't return string in Jupyter (prevents double display)
        else:
            print(markdown)
            return None
    except Exception:
        # Fallback if not in Jupyter
        print(markdown)
        return None


__all__ = [
    "__version__",
    "login",
    "logout",
    "reset",
    "get_sync_key",
    "sync",
    "decks",
    "delete_deck",
    "rename_deck",
    "upsert_deck",
    "load_deck",
    "create_deck",
    "sync_meta_raw",
    "sync_start_raw",
    "llmtxt",
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
    "OperationResult",
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
    # Check if we have a cached sync key
    cached_key = get_sync_key()
    if cached_key:
        print("RememberIt loaded! Logged in successfully.")
    else:
        print("RememberIt loaded! Login first:")
        print('  rememberit.login("email", "password")')
    print("\nThen try:")
    print("  rememberit.sync()")
    print("  rememberit.decks()")
    print("\nOr see all commands:")
    print("  rememberit.help()")
except NameError:
    # Not in IPython/Jupyter, skip the message
    pass
