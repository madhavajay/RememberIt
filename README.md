# RememberIt

[![PyPI version](https://badge.fury.io/py/rememberit.svg)](https://badge.fury.io/py/rememberit)
[![Python versions](https://img.shields.io/pypi/pyversions/rememberit.svg)](https://pypi.org/project/rememberit/)
[![License](https://img.shields.io/pypi/l/rememberit.svg)](https://github.com/madhavajay/rememberit/blob/main/LICENSE)

Python library for syncing flashcards with Anki.
Designed to be easily used by LLM Agents.

Don't just [solve.it.com](https://solve.it.com/?via_id=eil03t43&utm_source=rememberit) also RememberIt!

Create beautiful styled cards with syntax highlighting, embedded images, gradient themes, and more.

## Installation

```bash
pip install rememberit
```

## 📚 Tutorial

**Interactive Jupyter Notebook:** [tutorial.ipynb](./tutorial.ipynb)

Or run the built-in tutorial:
```python
import rememberit
rememberit.tutorial()  # Interactive walkthrough
```

## Quick Start

```python
import rememberit

# Login with your AnkiWeb credentials (first time only)
rememberit.login("email@example.com", "password")

# Sync and get your decks
decks = rememberit.sync()

# Create styled flashcards with code, images, and more!
deck_data = {
    "name": "Python Basics",
    "cards": [
        # Styled card (default) - random gradient theme
        {"front": "What is Python?", "back": "A programming language"},

        # Code answer with syntax highlighting
        {
            "front": "Write a function to add two numbers",
            "back": "def add(a, b):\n    return a + b",
            "back_type": "code",
        },

        # Styled question + code answer
        {
            "front": "How do you create a list comprehension?",
            "front_type": "card",
            "front_theme": "blue",
            "back": "[x**2 for x in range(10)]",
            "back_type": "code",
            "back_lang": "python",
        },

        # Images (auto-detected from paths or PIL)
        {
            "front": "System Architecture",
            "back": "~/diagrams/architecture.png",
        },
    ]
}
rememberit.upsert_deck(deck_data)
```

## Card Schema

```python
{
    "front": str | callable | Path | PIL.Image,  # Text, function, or image!
    "back": str | callable | Path | PIL.Image,   # Text, function, or image!
    "front_type": str,            # "card" (default) | "code" | "plain" | "image"
    "back_type": str,             # "card" (default) | "code" | "plain" | "image"
    "front_lang": str,            # For code type (default: "python")
    "back_lang": str,
    "front_theme": str,           # For card type (default: "random")
    "back_theme": str,
    "tags": str,                  # Space-separated tags
}
```

## Card Types

| Type | Description |
|------|-------------|
| `card` (default) | Styled card with gradient background |
| `code` | Syntax-highlighted code block |
| `image` | Embedded image (auto-detected) |
| `plain` | Plain text, no formatting |

## Card Themes

`random` (default), `gradient`, `dark`, `light`, `blue`, `purple`, `green`, `orange`

## Supported Languages

python, javascript, typescript, html, css, sql, bash, shell, json, yaml, rust, go, java, c, cpp, swift, kotlin, ruby, php, r, scala, haskell, lua, perl, markdown

## Core API

| Function | Description |
|----------|-------------|
| `login(email, password)` | Authenticate and save sync key |
| `logout()` | Clear saved credentials |
| `sync()` | Sync with AnkiWeb, return decks |
| `decks()` | Return cached decks |
| `create_deck(name)` | Create a new deck |
| `delete_deck(deck)` | Delete by name/id/object |
| `rename_deck(deck, new_name)` | Rename a deck |
| `upsert_deck(data)` | Add/update cards from dict/JSON |

## Formatting

| Function | Description |
|----------|-------------|
| `format_code(code, lang)` | Format code with syntax highlighting |
| `format_question(text, theme)` | Format text as styled card |
| `format_image(image, alt)` | Format image as embedded data URI |
| `auto_format_field(value)` | Auto-detect and format any field type |
| `extract_source(func)` | Extract source from function |
| `parse_card_field(html)` | Parse HTML back to plain text + metadata |

## Templates

Custom templates are stored in `~/.rememberit/templates/`

| Function | Description |
|----------|-------------|
| `show_templates()` | Display all templates with previews |
| `save_template(name, html)` | Save custom template |
| `get_template(name)` | Get template by name |
| `export_builtin(name)` | Export builtin to custom dir |

## Utilities

| Function | Description |
|----------|-------------|
| `signup()` | Show AnkiWeb registration instructions |
| `tutorial()` | Interactive walkthrough (creates real cards!) |
| `llmtxt()` | Show quickstart guide for AI agents |
| `help()` | Show API reference |
| `examples.code()` | Preview code formatting |
| `examples.questions()` | Preview card themes |
| `examples.images()` | Preview image examples |

## Export Deck as JSON

```python
# Get deck in upsert-compatible format
deck = rememberit.decks()["My Deck"]
deck.to_dict()  # Returns clean format with types parsed out
deck.json()     # Returns as JSON string

# Get raw HTML (old behavior)
deck.to_dict(raw=True)
```

## Pass Functions Directly

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

deck_data = {
    "name": "Code Examples",
    "cards": [
        {
            "front": "Fibonacci function",
            "back": fibonacci,  # Source extracted automatically!
        }
    ]
}
rememberit.upsert_deck(deck_data)
```

## Working with Images

Images are **automatically detected and converted** to embedded data URIs. No manual formatting needed!

### Supported Image Inputs

```python
from pathlib import Path
from PIL import Image

# 1. File paths (relative, absolute, or with ~)
card.update(back="~/Downloads/diagram.png")
card.update(back="/absolute/path/to/image.jpg")
card.update(back="relative/path/image.png")

# 2. Path objects
image_path = Path("~/Downloads/screenshot.png").expanduser()
card.update(back=image_path)

# 3. PIL Images
pil_image = Image.open("chart.png")
card.update(back=pil_image)

# 4. Objects with _repr_png_() or _repr_jpeg_() (matplotlib, etc.)
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])
card.update(back=fig)  # Auto-converted!

# 5. In upsert_deck
deck_data = {
    "name": "Visual Learning",
    "cards": [
        {
            "front": "System Architecture",
            "back": "~/diagrams/architecture.png",  # Auto-detected!
        },
        {
            "front": "Performance Graph",
            "back": pil_image,  # PIL Image works too!
            "back_type": "image",  # Optional: explicit type
        }
    ]
}
rememberit.upsert_deck(deck_data)
```

### Manual Image Formatting

If you need more control:

```python
from rememberit import format_image

# With custom alt text and size limit
html = format_image(
    "~/Downloads/photo.jpg",
    alt="Detailed diagram",
    max_bytes=1_000_000  # 1MB limit
)
card.update(back=html)
```

### What Works Everywhere

All these methods support images with auto-detection:
- `card.update(front=image, back=image)`
- `deck.add_card(front=image, back=image)`
- `upsert_deck({"cards": [{"front": image, "back": image}]})`

## License

Apache-2.0
