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
    auto_format_field,
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

__version__ = "0.1.12"

_client = RememberItClient()
auto_sync = True  # Set to False to disable automatic syncing


class _DecksProxy:
    """Proxy object that makes decks both callable and subscriptable."""

    def __call__(self) -> DeckCollection:
        """Return cached decks (syncing down if empty and auto_sync is True)."""
        return _client.decks(auto_sync=auto_sync)

    def __getitem__(self, key: str | int) -> Deck:
        """Get deck by name or index."""
        return self()[key]


decks = _DecksProxy()


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
        # Check if we're actually in an IPython/Jupyter environment
        from IPython import get_ipython  # type: ignore[attr-defined]
        from IPython.display import HTML, display

        if get_ipython() is not None:  # type: ignore[no-untyped-call]
            display(HTML(html))  # type: ignore[no-untyped-call]
        else:
            # IPython installed but not in interactive shell - use plain text
            import re

            print(re.sub(r"<[^>]+>", "", html))
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


def signup() -> None:
    """Show instructions for creating an AnkiWeb account."""
    login_code = """import rememberit
rememberit.login("your-email@example.com", "your-password")"""

    html = f"""
<div style="background:#1F1F1F;border:1px solid #3A3A3A;border-radius:12px;
padding:20px 24px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;
box-shadow:0 4px 12px rgba(0,0,0,0.15);">

<div style="color:#F5F5F5;font-weight:700;font-size:1.3em;margin-bottom:16px;">
📝 Create an AnkiWeb Account</div>

<div style="color:#d4d4d4;font-size:1em;line-height:1.8;margin-bottom:16px;">
To use RememberIt, you need a free AnkiWeb account.
</div>

<div style="color:#90EE90;font-weight:600;margin:16px 0 12px 0;">Setup Steps</div>
<ol style="color:#d4d4d4;margin:0;padding-left:20px;font-size:0.95em;line-height:2;">
<li>Visit: <a href="https://ankiweb.net/account/signup"
style="color:#87CEEB;text-decoration:none;">https://ankiweb.net/account/signup</a></li>
<li>Create your account with email and password</li>
<li>Come back and login:</li>
</ol>

<div style="margin:16px 0;">
{format_code(login_code, "python")}
</div>

<div style="color:#98FB98;font-size:0.95em;margin-top:16px;padding:12px;
background:#2A2A2A;border-left:3px solid #90EE90;border-radius:4px;">
✓ That's it! Your flashcards will sync to all your devices.
</div>

</div>"""
    _styled_output(html)


def tutorial() -> None:
    """Step-by-step tutorial showing how to create flashcards."""
    step1_code = """import rememberit

# First time setup
rememberit.login("your-email@example.com", "your-password")"""

    step2_code = """# Sync and get your decks
decks = rememberit.sync()
print(f"You have {len(decks)} deck(s)")"""

    step3_code = """# Create a new deck
deck = decks.get_or_create("My Tutorial Deck")"""

    step4_code = """# Add a simple styled text card
rememberit.upsert_deck({
    "name": "My Tutorial Deck",
    "cards": [
        {
            "front": "What is RememberIt?",
            "back": "A Python library for beautiful Anki flashcards"
        }
    ]
})"""

    step5_code = """# Add a code card - Method 1: Function object
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

deck = rememberit.upsert_deck({
    "name": "My Tutorial Deck",
    "cards": [
        {
            "front": "Write a factorial function",
            "back": factorial,  # Auto-extracts source!
            "tags": "python recursion"
        }
    ]
})  # Returns the deck!"""

    step6_code = """# Add a code card - Method 2: Plain text with language
sql_query = \"\"\"SELECT users.name, COUNT(orders.id) AS order_count
FROM users
LEFT JOIN orders ON users.id = orders.user_id
WHERE orders.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY users.id
HAVING order_count > 5
ORDER BY order_count DESC;\"\"\"

card = deck.add_card(
    front="Find active users with 5+ orders in last 30 days",
    back=sql_query,
    back_type="code",
    back_lang="sql",
    tags="sql database"
)  # Returns the card!

print("✓ Added code cards with syntax highlighting!")"""

    step7_code = """# Add an image card
rememberit.upsert_deck({
    "name": "My Tutorial Deck",
    "cards": [
        {
            "front": "System Architecture",
            "back": "~/diagrams/architecture.png"  # Auto-embedded!
        }
    ]
})"""

    step8_code = """# View your deck (both work!)
deck = rememberit.decks["My Tutorial Deck"]  # Subscriptable!
# or: deck = rememberit.decks()["My Tutorial Deck"]  # Callable
print(f"Cards: {len(deck.cards)}")

# Update a card
card = deck.cards[0]
card.update(back="Updated answer!")"""

    auto_sync_code = """# Control automatic syncing
rememberit.auto_sync = False  # Disable auto-sync
decks = rememberit.decks()    # Won't sync automatically

# Manual sync when needed
rememberit.sync()

rememberit.auto_sync = True   # Re-enable (default)"""

    solveit_code = """# Load RememberIt tools into solve.it
import rememberit

# Check if running in solve.it
if rememberit.is_solveit():
    rememberit.load_tools()  # Adds Anki tools to AI agent
    print("✓ RememberIt tools loaded!")

# Now the AI agent can create flashcards for you!
# Just ask: "Create flashcards about Python lists" """

    custom_theme_code = """# Create a custom gradient theme
from rememberit import save_template

custom_html = '''
<div style="background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);
padding:24px;border-radius:12px;color:white;font-size:1.1em;
box-shadow:0 4px 12px rgba(0,0,0,0.15);">
{{CONTENT}}
</div>'''

save_template("purple-gradient", custom_html)

# Use your custom theme
deck.add_card(
    front="Custom Theme Example",
    front_type="card",
    front_theme="purple-gradient",  # Your custom theme!
    back="This card uses a custom gradient"
)"""

    html = f"""
<div style="background:#1F1F1F;border:1px solid #3A3A3A;border-radius:12px;
padding:20px 24px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;
box-shadow:0 4px 12px rgba(0,0,0,0.15);">

<div style="color:#F5F5F5;font-weight:700;font-size:1.4em;margin-bottom:8px;">
🎓 RememberIt Tutorial</div>

<div style="margin-bottom:16px;">
<a href="https://github.com/madhavajay/RememberIt/blob/main/tutorial.ipynb"
target="_blank" rel="noopener"
style="color:#90EE90;text-decoration:none;font-size:0.9em;">
📓 View interactive tutorial on GitHub →</a>
</div>

<div style="color:#d4d4d4;font-size:1em;line-height:1.8;margin-bottom:20px;">
Follow these steps to create your first flashcards. Copy and run each code block in order.
</div>

<div style="color:#90EE90;font-weight:600;margin:20px 0 12px 0;">Step 1: Login</div>
{format_code(step1_code, "python")}

<div style="color:#87CEEB;font-weight:600;margin:20px 0 12px 0;">Step 2: Sync Your Decks</div>
{format_code(step2_code, "python")}

<div style="color:#DDA0DD;font-weight:600;margin:20px 0 12px 0;">Step 3: Create a Deck</div>
{format_code(step3_code, "python")}

<div style="color:#FFD700;font-weight:600;margin:20px 0 12px 0;">Step 4: Add Styled Text Card</div>
{format_code(step4_code, "python")}
<div style="color:#888;font-size:0.9em;margin-top:8px;">
💡 Cards are auto-styled with gradient backgrounds by default
</div>

<div style="color:#FFA07A;font-weight:600;margin:20px 0 12px 0;">
Step 5: Add Code Card (Function)</div>
{format_code(step5_code, "python")}
<div style="color:#888;font-size:0.9em;margin-top:8px;">
💡 Pass function objects - source is extracted automatically!
</div>

<div style="color:#98FB98;font-weight:600;margin:20px 0 12px 0;">Step 6: Add Code Card (SQL)</div>
{format_code(step6_code, "python")}
<div style="color:#888;font-size:0.9em;margin-top:8px;">
💡 Plain text with language specification for syntax highlighting
</div>

<div style="color:#87CEEB;font-weight:600;margin:20px 0 12px 0;">Step 7: Add Image Card</div>
{format_code(step7_code, "python")}
<div style="color:#888;font-size:0.9em;margin-top:8px;">
💡 Images from paths, PIL objects, or matplotlib figures are auto-embedded
</div>

<div style="color:#DDA0DD;font-weight:600;margin:20px 0 12px 0;">Step 8: View & Update Cards</div>
{format_code(step8_code, "python")}

<div style="color:#FFA07A;font-weight:600;margin:20px 0 12px 0;">⚙️ Auto-Sync Control</div>
{format_code(auto_sync_code, "python")}
<div style="color:#888;font-size:0.9em;margin-top:8px;">
💡 By default,
<code style="background:#1a1a1a;padding:2px 6px;border-radius:3px;">decks()</code>
syncs if cache is empty. Set
<code style="background:#1a1a1a;padding:2px 6px;border-radius:3px;">auto_sync = False</code>
for manual control.
</div>

<div style="color:#90EE90;font-weight:600;margin:20px 0 12px 0;">
🤖 Solve.it Integration</div>
{format_code(solveit_code, "python")}
<div style="color:#888;font-size:0.9em;margin-top:8px;">
💡 Use with <a href="https://solve.it.com/?via_id=eil03t43"
style="color:#87CEEB;text-decoration:none;">solve.it</a> -
AI agents can create flashcards automatically!
</div>

<div style="color:#DDA0DD;font-weight:600;margin:20px 0 12px 0;">
🎨 Custom Themes</div>
{format_code(custom_theme_code, "python")}
<div style="color:#888;font-size:0.9em;margin-top:8px;">
💡 Create your own card styles with custom HTML and CSS gradients
</div>

<div style="color:#FFD700;font-weight:600;margin:24px 0 12px 0;">✨ Next Steps</div>
<ul style="color:#d4d4d4;margin:0;padding-left:20px;font-size:0.95em;line-height:2;">
<li>Open Anki desktop app to review your cards</li>
<li>Try different themes:
<code style="background:#272822;color:#f8f8f2;padding:2px 6px;border-radius:3px;">blue</code>,
<code style="background:#272822;color:#f8f8f2;padding:2px 6px;border-radius:3px;">purple</code>,
<code style="background:#272822;color:#f8f8f2;padding:2px 6px;border-radius:3px;">gradient</code>
</li>
<li>Explore:
<code style="background:#272822;color:#f8f8f2;padding:2px 6px;border-radius:3px;">
rememberit.help()</code></li>
<li>Preview examples:
<code style="background:#272822;color:#f8f8f2;padding:2px 6px;border-radius:3px;">
rememberit.examples.code()</code></li>
<li>For AI agents:
<code style="background:#272822;color:#f8f8f2;padding:2px 6px;border-radius:3px;">
rememberit.llmtxt()</code></li>
</ul>

<div style="color:#98FB98;font-size:0.95em;margin-top:20px;padding:12px;
background:#2A2A2A;border-left:3px solid #90EE90;border-radius:4px;">
📚 Interactive Notebook: Check out
<a href="https://github.com/madhavajay/RememberIt/blob/main/tutorial.ipynb"
style="color:#90EE90;text-decoration:none;">tutorial.ipynb</a>
for a complete walkthrough with live examples!
</div>

</div>"""
    _styled_output(html)


__all__ = [
    "__version__",
    "auto_sync",
    "login",
    "logout",
    "signup",
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
    "format_image",
    "format_question",
    "auto_format_field",
    "extract_source",
    "parse_card_field",
    "SUPPORTED_LANGUAGES",
    "examples",
    # Utilities
    "add_demo",
    "list_decks_and_cards",
    "tutorial",
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

# Show welcome message on import
_solveit_section = ""
if is_solveit():
    _solveit_section = """
<div style="color:#d4d4d4;font-size:0.95em;margin-top:8px;padding-top:8px;
border-top:1px solid #3A3A3A;">
🔧 Run <code style="background:#272822;color:#f8f8f2;padding:2px 6px;
border-radius:4px;font-family:monospace;">rememberit.load_tools()</code>
to add Anki tools to solve.it
</div>"""

_welcome_html = f"""
<div style="background:#1F1F1F;border:1px solid #3A3A3A;border-radius:10px;
padding:16px 20px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;
box-shadow:0 4px 12px rgba(0,0,0,0.15);">

<div style="color:#F5F5F5;font-weight:600;font-size:1.1em;margin-bottom:12px;">
🎓 Welcome to RememberIt!</div>

<div style="color:#d4d4d4;font-size:0.95em;line-height:1.6;">

<div style="margin-bottom:8px;">
💡 Run <code style="background:#272822;color:#f8f8f2;padding:2px 6px;
border-radius:4px;font-family:monospace;">rememberit.tutorial()</code>
to learn how to use it
</div>

<div>
📓 <a href="https://github.com/madhavajay/RememberIt/blob/main/tutorial.ipynb"
target="_blank" rel="noopener"
style="color:#90EE90;text-decoration:none;">
Interactive tutorial on GitHub →</a>
</div>
{_solveit_section}
</div>

</div>"""

_styled_output(_welcome_html)
