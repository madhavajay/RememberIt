from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import examples
from .client import (
    RememberItClient,
    RememberItError,
    Session,
    add_demo,
    list_decks_and_cards,
    load_session,
)
from .config import Settings, config_path, load_settings, save_settings
from .formatting import (
    SUPPORTED_LANGUAGES,
    extract_source,
    format_code,
    format_image,
    format_question,
    parse_card_field,
)
from .models import (
    Card,
    CardCollection,
    CardSummary,
    Deck,
    DeckCollection,
    DeckListResult,
    OperationResult,
)
from .templates import (
    delete_template,
    export_builtin,
    get_template,
    list_templates,
    render_template,
    save_template,
    show_templates,
    template_info,
)
from .tools import TOOLS, is_solveit, load_tools, tools_info, tools_registered

__version__ = "0.1.7"

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


def _process_card_field(
    value: object, field_type: str | None, lang: str, theme: str = "gradient"
) -> str:
    """Process a card field, applying formatting based on type."""
    if field_type == "code":
        return format_code(value, language=lang)  # type: ignore[arg-type]
    if field_type == "image":
        return format_image(value)
    if field_type == "plain":
        # If user asked for plain but handed us an image-like object, still render it as image.
        is_image = hasattr(value, "_repr_png_") or hasattr(value, "_repr_jpeg_")
        if not isinstance(value, str) and is_image:
            return format_image(value)
        if isinstance(value, (str, Path)):
            maybe_img = _try_format_image(value)
            if maybe_img is not None:
                return maybe_img
        return value if isinstance(value, str) else str(value)
    # Auto-detect image objects when type is not specified
    if field_type is None and (hasattr(value, "_repr_png_") or hasattr(value, "_repr_jpeg_")):
        return format_image(value)
    if field_type is None and isinstance(value, (str, Path)):
        maybe_img = _try_format_image(value)
        if maybe_img is not None:
            return maybe_img
    text_val = value if isinstance(value, str) else str(value)
    # Default to "card" styling
    return format_question(text_val, theme=theme)


def _try_format_image(value: object) -> str | None:
    """Best-effort image rendering for paths/base64/data URIs; returns None if unsupported."""
    try:
        return format_image(value)
    except ValueError:
        # Too large or other validation issues - let caller decide whether to surface
        raise
    except Exception:
        return None


def upsert_deck(data: str | Mapping[str, Any], *, deck_name: str | None = None) -> Deck:
    """
    Create or update a deck with cards from a dict or JSON file.

    Schema:
        {
            "name": str,
            "cards": [
                {
                    "front": str | callable,  # Can be a function object!
                    "back": str | callable,
                    "note_id"?: int,
                    "tags"?: str,
                    "front_type"?: "code" | "plain",  # Default: styled card
                    "front_lang"?: str (default: "python"),
                    "front_theme"?: str (default: "random"),
                    "back_type"?: "code" | "plain",   # Default: styled card
                    "back_lang"?: str (default: "python"),
                    "back_theme"?: str (default: "random"),
                }
            ]
        }

    Field types:
        - "code": Syntax-highlighted code block (use with front_lang/back_lang)
        - "image": Data-URI image (path/base64/_repr_png_/bytes)
        - "plain": Plain text, no styling
        - Default (no type): Styled card with gradient background

    Themes: random (default), gradient, dark, light, blue, purple, green, orange

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
        raw_front = card.get("front", "")
        raw_back = card.get("back", "")
        tags = card.get("tags", "")
        note_id = card.get("note_id")

        front_type = card.get("front_type")
        front_lang = card.get("front_lang", "python")
        front_theme = card.get("front_theme", "random")
        back_type = card.get("back_type")
        back_lang = card.get("back_lang", "python")
        back_theme = card.get("back_theme", "random")

        # Handle callable objects (functions) - extract source
        if callable(raw_front) and not isinstance(raw_front, str):
            raw_front = extract_source(raw_front)
            if not front_type:
                front_type = "code"
        if callable(raw_back) and not isinstance(raw_back, str):
            raw_back = extract_source(raw_back)
            if not back_type:
                back_type = "code"

        front = _process_card_field(raw_front, front_type, front_lang, front_theme)
        back = _process_card_field(raw_back, back_type, back_lang, back_theme)

        if note_id:
            # Explicit note_id - always update
            _client.update_card(
                note_id=note_id, front=front, back=back, tags=tags, deck_id=deck_obj.id
            )
        else:
            # Try to find existing card by raw_front OR processed front
            # (handles both plain text and already-formatted cards)
            existing = existing_fronts.get(raw_front) or existing_fronts.get(front)

            if existing and existing.id is not None:
                # Update if front, back, or tags changed
                needs_update = (
                    existing.front != front
                    or existing.back != back
                    or (tags and tags != getattr(existing, "tags", ""))
                )
                if needs_update:
                    _client.update_card(
                        note_id=existing.id,
                        front=front,
                        back=back,
                        tags=tags,
                        deck_id=deck_obj.id,
                    )
            else:
                # New card
                _client.add_card(deck_id=deck_obj.id, front=front, back=back, tags=tags)

    _client.sync_up()
    deck_obj.sync()
    return deck_obj


# Backwards compatibility alias
def load_deck(data: str | Mapping[str, Any], *, deck_name: str | None = None) -> Deck:
    return upsert_deck(data, deck_name=deck_name)


def _styled_output(html: str) -> None:
    """Display styled HTML in notebook, falls back to print."""
    try:
        from IPython.display import HTML, display

        display(HTML(html))  # type: ignore[no-untyped-call]
    except ImportError:
        import re

        print(re.sub(r"<[^>]+>", "", html))


def llmtxt() -> None:
    """Display quickstart for LLM editing."""
    example_code = """import rememberit

# rememberit.login("email@example.com", "password")  # first time only
decks = rememberit.sync()

deck_data = {
    "name": "Python Basics",
    "cards": [
        # Styled card (default) - random gradient theme
        {"front": "What is Python?", "back": "A programming language"},

        # Code answer with syntax highlighting
        {
            "front": "Write a function to add two numbers",
            "back": "def add(a, b):\\n    return a + b",
            "back_type": "code",
        },
    ]
}
rememberit.upsert_deck(deck_data)"""

    schema_code = """{
    "front": str | callable,      # Question (or pass a function!)
    "back": str | callable,       # Answer (or pass a function!)
    "front_type": str,            # Default: styled card | "code" | "plain"
    "back_type": str,             # Default: styled card | "code" | "plain"
    "front_lang": str,            # For code type (default: "python")
    "back_lang": str,
    "front_theme": str,           # For card type (default: "random")
    "back_theme": str,
    "tags": str,                  # Space-separated tags
}"""

    cs = (
        "background:#272822;color:#f8f8f2;padding:3px 8px;"
        "border-radius:4px;font-family:'Fira Code',monospace;font-size:0.9em"
    )
    td = "padding:8px 12px;border:1px solid #444"
    th = "padding:8px 12px;border:1px solid #444;color:#f8f8f2;text-align:left"

    html = f"""
<div style="background:#1F1F1F;border:1px solid #3A3A3A;border-radius:12px;
padding:20px 24px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;
box-shadow:0 4px 12px rgba(0,0,0,0.15);">

<div style="color:#F5F5F5;font-weight:700;font-size:1.3em;margin-bottom:16px;">
🃏 RememberIt - Anki Flashcard API</div>

<div style="color:#90EE90;font-weight:600;margin:16px 0 8px 0;">Quick Start</div>
{format_code(example_code, "python")}

<div style="color:#87CEEB;font-weight:600;margin:20px 0 8px 0;">Card Schema</div>
{format_code(schema_code, "python")}

<div style="color:#DDA0DD;font-weight:600;margin:20px 0 12px 0;">Types</div>
<table style="border-collapse:collapse;width:100%;margin-bottom:16px;">
<thead><tr style="background:#272822;">
<th style="{th}">Type</th><th style="{th}">Description</th>
</tr></thead>
<tbody style="color:#d4d4d4;">
<tr><td style="{td}">(default)</td>
<td style="{td}">Styled card with random gradient</td></tr>
<tr><td style="{td}"><code style="{cs}">code</code></td>
<td style="{td}">Syntax-highlighted code block</td></tr>
<tr><td style="{td}"><code style="{cs}">plain</code></td>
<td style="{td}">Plain text, no formatting</td></tr>
</tbody></table>

<div style="color:#FFD700;font-weight:600;margin:16px 0 8px 0;">Code Languages</div>
<div style="color:#d4d4d4;font-size:0.9em;line-height:1.6;">
python, javascript, typescript, html, css, sql, bash, shell, json, yaml,
rust, go, java, c, cpp, swift, kotlin, ruby, php, r, scala, haskell, lua, perl, markdown
</div>

<div style="color:#FFA07A;font-weight:600;margin:16px 0 8px 0;">Card Themes</div>
<div style="color:#d4d4d4;font-size:0.9em;">
<code style="{cs}">random</code> (default),
<code style="{cs}">gradient</code>,
<code style="{cs}">dark</code>,
<code style="{cs}">light</code>,
<code style="{cs}">blue</code>,
<code style="{cs}">purple</code>,
<code style="{cs}">green</code>,
<code style="{cs}">orange</code>
</div>

<div style="color:#98FB98;font-weight:600;margin:20px 0 8px 0;">💡 Tips</div>
<ul style="color:#d4d4d4;margin:0;padding-left:20px;font-size:0.9em;line-height:1.8;">
<li>Pass a function object as front/back → source auto-extracted, type auto-set to "code"</li>
<li>Run <code style="{cs}">rememberit.examples.code()</code> to preview all language formatting</li>
<li>Run <code style="{cs}">rememberit.examples.questions()</code> to preview all card themes</li>
</ul>

</div>"""
    _styled_output(html)


def help() -> None:  # noqa: A001
    """Show available commands."""
    cs = (
        "background:#272822;color:#f8f8f2;padding:3px 8px;"
        "border-radius:4px;font-family:'Fira Code',monospace;font-size:0.85em"
    )
    td = "padding:10px 14px;border:1px solid #444"
    th = "padding:10px 14px;border:1px solid #444;color:#f8f8f2;text-align:left;font-weight:600"

    api_funcs = [
        ("login(email, password)", "Authenticate and save sync key"),
        ("logout()", "Clear saved credentials"),
        ("sync()", "Sync with AnkiWeb, return decks"),
        ("decks()", "Return cached decks"),
        ("create_deck(name)", "Create a new deck"),
        ("delete_deck(deck)", "Delete by name/id/object"),
        ("rename_deck(deck, new_name)", "Rename a deck"),
        ("upsert_deck(data)", "Add/update cards from dict/JSON"),
    ]

    format_funcs = [
        ("format_code(code, lang)", "Format code with syntax highlighting"),
        ("format_question(text, theme)", "Format text as styled card"),
        ("extract_source(func)", "Extract source from function"),
    ]

    template_funcs = [
        ("show_templates()", "Display all templates with previews"),
        ("save_template(name, html)", "Save custom template"),
        ("get_template(name)", "Get template by name"),
        ("export_builtin(name)", "Export builtin to custom dir"),
    ]

    util_funcs = [
        ("llmtxt()", "Show quickstart guide"),
        ("help()", "Show API reference"),
        ("examples.code()", "Preview code formatting"),
        ("examples.questions()", "Preview card themes"),
    ]

    def make_table(funcs: list[tuple[str, str]]) -> str:
        rows = "\n".join(
            f'<tr><td style="{td}"><code style="{cs}">{f}</code></td><td style="{td}">{d}</td></tr>'
            for f, d in funcs
        )
        return f"""<table style="border-collapse:collapse;width:100%;margin-bottom:16px;">
<thead><tr style="background:#272822;">
<th style="{th}">Function</th><th style="{th}">Description</th>
</tr></thead>
<tbody style="color:#d4d4d4;">{rows}</tbody></table>"""

    html = f"""
<div style="background:#1F1F1F;border:1px solid #3A3A3A;border-radius:12px;
padding:20px 24px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;
box-shadow:0 4px 12px rgba(0,0,0,0.15);">

<div style="color:#F5F5F5;font-weight:700;font-size:1.3em;margin-bottom:20px;">
RememberIt API Reference</div>

<div style="color:#90EE90;font-weight:600;margin:16px 0 10px 0;">Core API</div>
{make_table(api_funcs)}

<div style="color:#87CEEB;font-weight:600;margin:16px 0 10px 0;">Formatting</div>
{make_table(format_funcs)}

<div style="color:#FFD700;font-weight:600;margin:16px 0 10px 0;">Templates</div>
{make_table(template_funcs)}

<div style="color:#DDA0DD;font-weight:600;margin:16px 0 10px 0;">Utilities</div>
{make_table(util_funcs)}

<div style="color:#888;font-size:0.85em;margin-top:16px;">
v{__version__} • Custom templates: <code style="{cs}">~/.rememberit/templates/</code>
</div>

</div>"""
    _styled_output(html)


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
    # Formatting
    "format_code",
    "format_question",
    "extract_source",
    "parse_card_field",
    "SUPPORTED_LANGUAGES",
    "examples",
    # Utilities
    "add_demo",
    "list_decks_and_cards",
    "llmtxt",
    "help",
    # Classes
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
    # Templates
    "show_templates",
    "save_template",
    "get_template",
    "delete_template",
    "export_builtin",
    "list_templates",
    "render_template",
    "template_info",
    # Solveit tools
    "is_solveit",
    "tools_registered",
    "load_tools",
    "tools_info",
    "TOOLS",
]

# Auto-detect solveit and show hint
if is_solveit():
    print("Run rememberit.load_tools() to add Anki tools to solveit.")
