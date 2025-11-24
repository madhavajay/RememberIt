# RememberIt

[![PyPI version](https://badge.fury.io/py/rememberit.svg)](https://badge.fury.io/py/rememberit)
[![Python versions](https://img.shields.io/pypi/pyversions/rememberit.svg)](https://pypi.org/project/rememberit/)
[![License](https://img.shields.io/pypi/l/rememberit.svg)](https://github.com/madhavajay/rememberit/blob/main/LICENSE)

Python library for syncing flashcards with Anki.

## Installation

```bash
uv pip install -U rememberit
```

## Quick Start

```python
import rememberit

# Login with your AnkiWeb credentials
rememberit.login("email@example.com", "password")

# Sync and get your decks
decks = rememberit.sync()

# Add or update cards in bulk
deck_data = {
    "name": "My Deck",
    "cards": [
        {"front": "Question 1", "back": "Answer 1"},
        {"front": "Question 2", "back": "Answer 2"},
    ]
}
rememberit.upsert_deck(deck_data)
```

## LLM Text
```python
decks = rememberit.llmtxt()
```

Prints text so your LLM can know how to use rememberit.

## API

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

## License

Apache-2.0
