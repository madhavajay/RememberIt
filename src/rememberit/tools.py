"""Solveit LLM tools for RememberIt.

Tools are only registered when running inside a solveit dialog context.
In normal Jupyter, this module is a no-op.
"""

from __future__ import annotations

from inspect import currentframe

_SOLVEIT_AVAILABLE = False
_TOOLS_REGISTERED = False
_dh = None


def _in_solveit_context() -> bool:
    """Check if we're running inside a solveit dialog."""
    frame = currentframe()
    if frame is None:
        return False
    frame = frame.f_back
    while frame:
        if "__dialog_name" in frame.f_globals or "__dialog_name" in frame.f_locals:
            return True
        frame = frame.f_back
    return False


def _check_solveit() -> bool:
    """Check if dialoghelper is available and we're in solveit context."""
    global _SOLVEIT_AVAILABLE, _dh
    if _SOLVEIT_AVAILABLE:
        return True
    try:
        import dialoghelper as dh

        _dh = dh
        _SOLVEIT_AVAILABLE = True
        return True
    except ImportError:
        return False


def is_solveit() -> bool:
    """Returns True if running inside solveit dialog context."""
    return _check_solveit() and _in_solveit_context()


def list_decks() -> str:
    """List all available Anki decks with their card counts.

    **Workflow to update a deck:**
    1. rememberit_list_decks() - see available decks
    2. rememberit_deck_as_dict("DeckName") - get deck as editable dict
    3. Edit the cards as needed
    4. rememberit.upsert_deck(deck_data) - submit changes
    """
    import rememberit

    collection = rememberit.decks()
    if not collection:
        return "No decks found. Try `rememberit_sync_anki()` first."
    lines = [
        "| # | Deck | Cards |",
        "|---|------|-------|",
    ]
    for i, deck in enumerate(collection):
        lines.append(f"| {i} | {deck.path} | {len(deck.cards)} |")
    lines.append("")
    lines.append('**Next:** Use `rememberit_deck_as_dict("DeckName")` to get deck contents.')
    return "\n".join(lines)


def get_deck(deck_name: str) -> str:
    """Get a deck's cards as JSON for viewing/editing.

    Args:
        deck_name: Name or path of the deck to retrieve
    """
    import rememberit

    collection = rememberit.decks()
    try:
        deck = collection[deck_name]
        deck.sync()
        return deck.json()
    except KeyError:
        return f"Deck '{deck_name}' not found. Use rememberit_list_decks() to see available decks."


def add_card(
    deck_name: str,
    front: str,
    back: str,
    front_type: str | None = None,
    back_type: str | None = None,
    front_theme: str | None = None,
    back_theme: str | None = None,
    tags: str = "",
) -> str:
    """Add a flashcard to a deck.

    By default, creates styled gradient cards. For code answers, use
    `rememberit_add_code_card` or set back_type="code".

    Args:
        deck_name: Name of the deck (created if doesn't exist)
        front: Front side of the card (question)
        back: Back side of the card (answer)
        front_type: Optional - "code" or "plain" (default: styled card)
        back_type: Optional - "code" or "plain" (default: styled card)
        front_theme: Card theme - "random", "gradient", "dark", "light",
                     "blue", "purple", "green", "orange" (default: "random")
        back_theme: Theme for back side (default: "random")
        tags: Optional space-separated tags

    **Examples:**
    ```
    # Styled card (default)
    rememberit_add_card("Python", "What is a list?", "An ordered collection")

    # Code answer
    rememberit_add_card("Python", "Reverse a list", "my_list[::-1]", back_type="code")

    # Themed card
    rememberit_add_card("Python", "Important!", "Answer", front_theme="purple")
    ```
    """
    import rememberit

    card: dict[str, str | None] = {
        "front": front,
        "back": back,
        "front_type": front_type,
        "back_type": back_type,
        "front_theme": front_theme,
        "back_theme": back_theme,
        "tags": tags if tags else None,
    }
    # Remove None values
    filtered_card = {k: v for k, v in card.items() if v is not None}
    card_data = {"name": deck_name, "cards": [filtered_card]}
    rememberit.upsert_deck(card_data)
    theme_used = front_theme or back_theme or "random"
    theme_info = f" (theme={theme_used})" if front_theme or back_theme else ""
    return f"✓ Card added to '{deck_name}'{theme_info}"


def add_code_card(
    deck_name: str, front: str, back: str, language: str = "python", tags: str = ""
) -> str:
    """Add a code flashcard with syntax highlighting.

    Use this for programming questions where the answer is code.
    The back will be syntax-highlighted in the specified language.

    Args:
        deck_name: Name of the deck (created if doesn't exist)
        front: Front side (question about code)
        back: Back side (the code - will be syntax highlighted)
        language: Programming language (python, javascript, typescript, etc.)
        tags: Optional space-separated tags

    **Example:**
    ```
    rememberit_add_code_card(
        "Python",
        "Write a function to reverse a string",
        "def reverse(s):\\n    return s[::-1]",
        "python"
    )
    ```
    """
    import rememberit

    card_data = {
        "name": deck_name,
        "cards": [
            {
                "front": front,
                "back": back,
                "back_type": "code",
                "back_lang": language,
                "tags": tags,
            }
        ],
    }
    rememberit.upsert_deck(card_data)
    return f"✓ Code card ({language}) added to '{deck_name}'"


def add_cards(deck_name: str, cards_json: str) -> str:
    """Add multiple flashcards to a deck from JSON.

    Args:
        deck_name: Name of the deck (created if doesn't exist)
        cards_json: JSON array of cards

    **Card format:**
    ```json
    [
        {"front": "Question?", "back": "Answer"},
        {"front": "Code Q", "back": "def foo(): pass", "back_type": "code"},
        {"front": "Styled", "front_theme": "blue", "back": "Answer"}
    ]
    ```

    **Default:** Styled gradient cards (no type needed)
    **Types:** "code" (syntax highlighted), "plain" (no styling)
    **Themes:** random, gradient, dark, light, blue, purple, green, orange

    **Tip:** Use `rememberit.upsert_deck(deck_data)` for bulk add/update with deck name.
    """
    import json

    import rememberit

    cards = json.loads(cards_json)
    if not isinstance(cards, list):
        return "Error: cards_json must be a JSON array"

    collection = rememberit.decks()
    deck = collection[deck_name]

    added = 0
    for card in cards:
        front = card.get("front", "")
        back = card.get("back", "")
        if front and back:
            # Pass all card parameters to add_card
            deck.add_card(
                front=front,
                back=back,
                tags=card.get("tags", ""),
                front_type=card.get("front_type"),
                back_type=card.get("back_type"),
                front_lang=card.get("front_lang"),
                back_lang=card.get("back_lang"),
                front_theme=card.get("front_theme"),
                back_theme=card.get("back_theme"),
            )
            added += 1

    return f"✓ Added {added} cards to '{deck_name}'"


def update_card(
    deck_name: str,
    card_front: str,
    new_front: str = "",
    new_back: str = "",
    front_type: str | None = None,
    back_type: str | None = None,
    front_theme: str | None = None,
    back_theme: str | None = None,
    front_lang: str | None = None,
    back_lang: str | None = None,
    tags: str = "",
) -> str:
    """Update an existing card by matching its front text.

    Args:
        deck_name: Name of the deck containing the card
        card_front: Current front text to find the card
        new_front: New front text (empty = keep current)
        new_back: New back text (empty = keep current)
        front_type: Optional - "code" or "plain" (omit to keep styled)
        back_type: Optional - "code" or "plain" (omit to keep styled)
        front_theme: Card theme for front
        back_theme: Card theme for back
        front_lang: Language for code highlighting (front)
        back_lang: Language for code highlighting (back)
        tags: Space-separated tags

    **Examples:**
    ```
    # Update back to code
    rememberit_update_card("Python", "Reverse a list", new_back="my_list[::-1]",
                          back_type="code", back_lang="python")

    # Change theme
    rememberit_update_card("Python", "Important Q", front_theme="purple")
    ```
    """
    import rememberit

    collection = rememberit.decks()
    try:
        deck = collection[deck_name]
        deck.sync()
        card = deck.cards[card_front]
        card.update(
            front=new_front if new_front else None,
            back=new_back if new_back else None,
            front_type=front_type,
            back_type=back_type,
            front_theme=front_theme,
            back_theme=back_theme,
            front_lang=front_lang,
            back_lang=back_lang,
            tags=tags if tags else "",
        )
        return f"✓ Card updated in '{deck_name}'"
    except KeyError:
        return f"Card with front '{card_front}' not found in '{deck_name}'"


def create_deck(name: str) -> str:
    """Create a new empty deck.

    Args:
        name: Name for the new deck (use :: for hierarchy, e.g. "Parent::Child")
    """
    import rememberit

    rememberit.create_deck(name)
    return f"✓ Deck '{name}' created"


def delete_deck(name: str) -> str:
    """Delete a deck and all its cards.

    Args:
        name: Name of the deck to delete
    """
    import rememberit

    rememberit.delete_deck(name)
    return f"✓ Deck '{name}' deleted"


def sync_anki() -> str:
    """Sync with AnkiWeb to get latest changes."""
    import rememberit

    collection = rememberit.sync()
    total_cards = sum(len(d.cards) for d in collection)
    return f"✓ Synced {len(collection)} decks, {total_cards} total cards"


def upsert_deck(deck_json: str) -> str:
    """Create or update a deck with cards from JSON (RECOMMENDED).

    This is the main way to add/update cards. Cards with matching front text
    are updated; new cards are added.

    Args:
        deck_json: JSON object with name and cards array

    **Format:**
    ```json
    {
        "name": "Deck Name",
        "cards": [
            {"front": "Question?", "back": "Answer"},
            {"front": "Code Q", "back": "def foo(): pass", "back_type": "code"},
            {"front": "Styled", "front_theme": "blue", "back": "Answer"}
        ]
    }
    ```

    **Types:** "code" (syntax highlighted), "plain" (no styling), or omit for styled
    **Themes:** random, gradient, dark, light, blue, purple, green, orange
    **Languages:** python, javascript, typescript, html, css, sql, bash, json, etc.
    """
    import json

    import rememberit

    data = json.loads(deck_json)
    deck = rememberit.upsert_deck(data)
    return f"✓ Upserted deck '{deck.name}' with {len(deck.cards)} cards"


def deck_as_dict(deck_key: str) -> str:
    """Get a deck as a dictionary in upsert-compatible format.

    Returns the deck with parsed card content (not raw HTML).
    Edit the cards and resubmit via rememberit.upsert_deck().

    Args:
        deck_key: Deck name (string) or index number (as string, e.g. "0" for first deck)

    **Workflow:**
    1. Get deck: `rememberit_deck_as_dict("MyDeck")`
    2. Edit the cards array as needed
    3. Submit: `rememberit.upsert_deck(deck_data)` in Python
    """
    import json

    import rememberit

    collection = rememberit.decks()
    try:
        if deck_key.isdigit():
            deck = collection[int(deck_key)]
        else:
            deck = collection[deck_key]
        deck.sync()
        result = deck.to_dict()
        output = json.dumps(result, indent=2, ensure_ascii=False)
        hint = "\n\n**Next:** Edit cards, then: `rememberit.upsert_deck(deck_data)`"
        return output + hint
    except (KeyError, IndexError):
        return f"Deck '{deck_key}' not found. Use rememberit_list_decks()."


def list_card_types() -> str:
    """List all available card types, themes, and code languages.

    Use this to see formatting options for rememberit_add_card and rememberit_upsert_deck.
    """
    return """**Card Types:**
| Type | Description |
|------|-------------|
| (default) | Styled card with gradient background - just omit type parameter |
| code | Syntax-highlighted code block |
| plain | Plain text, no styling |

**Themes (for styled cards):**
| Theme | Description |
|-------|-------------|
| random | Random gradient (DEFAULT) |
| gradient | Purple-pink gradient |
| dark | Dark blue gradient |
| light | Light gray gradient |
| blue | Blue-cyan gradient |
| purple | Purple-magenta gradient |
| green | Green gradient |
| orange | Orange-yellow gradient |

**Languages (for type="code"):**
python, javascript, typescript, html, css, sql, bash, shell, json, yaml,
rust, go, java, c, cpp, swift, kotlin, ruby, php, r, scala, haskell

**Usage Examples:**
```python
# Styled card (default - no type needed)
rememberit_add_card("Deck", "Question", "Answer")

# Themed styled card
rememberit_add_card("Deck", "Important!", "Answer", front_theme="purple")

# Code card
rememberit_add_card("Deck", "Q", "code here", back_type="code")

# Code card helper
rememberit_add_code_card("Deck", "Q", "def foo(): pass", "python")

# Plain text (no styling)
rememberit_add_card("Deck", "Q", "A", front_type="plain", back_type="plain")
```
"""


def show_help() -> str:
    """Show RememberIt API reference and available commands."""
    return """# RememberIt API Reference

## Core API

| Function | Description |
|----------|-------------|
| `login(email, password)` | Authenticate and save sync key |
| `logout()` | Clear saved credentials |
| `sync()` | Sync with AnkiWeb, return decks |
| `decks()` | Return cached decks (auto-syncs if empty) |
| `decks["name"]` | Get deck by name (subscriptable) |
| `create_deck(name)` | Create a new deck |
| `delete_deck(deck)` | Delete by name/id/object |
| `rename_deck(deck, new_name)` | Rename a deck |
| `upsert_deck(data)` | Add/update cards from dict/JSON |

## Configuration

```python
rememberit.auto_sync = False  # Disable auto-sync on decks()
```

## Working with Decks

```python
# Get all decks
decks = rememberit.decks()

# Access deck by name or index
deck = rememberit.decks["Python Basics"]  # By name
deck = decks[0]  # By index

# Create/update deck with cards
deck = rememberit.upsert_deck({
    "name": "My Deck",
    "cards": [
        {"front": "Question?", "back": "Answer"},  # Styled card (default)
        {"front": "Code?", "back": "x = 1", "back_type": "code"},
    ]
})
```

## Adding Cards

```python
# Simple styled card (default)
card = deck.add_card(front="What is Python?", back="A programming language")

# Code card
card = deck.add_card(
    front="Reverse a list",
    back="my_list[::-1]",
    back_type="code",
    back_lang="python"
)

# Themed card
card = deck.add_card(
    front="Important concept",
    back="The answer",
    front_theme="purple",
    back_theme="dark"
)

# Plain text (no styling)
card = deck.add_card(
    front="Simple question",
    back="Simple answer",
    front_type="plain",
    back_type="plain"
)
```

## Updating Cards

```python
# Get card and update
card = deck.cards[0]  # By index
card = deck.cards["What is Python?"]  # By fuzzy search

# Update with styled text (default)
card.update(back="New answer")

# Update with code
card.update(back="def foo(): pass", back_type="code", back_lang="python")

# Update with plain text
card.update(back="Plain answer", back_type="plain")
```

## Card Schema

```python
{
    "name": "Deck Name",
    "cards": [
        {
            "front": str,            # Question text
            "back": str,             # Answer text
            "front_type": str,       # "code" | "plain" | omit for styled (default)
            "back_type": str,        # "code" | "plain" | omit for styled (default)
            "front_lang": str,       # For code: python, javascript, etc.
            "back_lang": str,
            "front_theme": str,      # random, gradient, dark, light, blue, purple, green, orange
            "back_theme": str,
            "tags": str,             # Space-separated tags
        }
    ]
}
```

**Default Behavior:** Cards are styled with gradient themes unless you
specify `type="code"` or `type="plain"`

## Workflow Example

```python
import rememberit

# Login once
rememberit.login("you@example.com", "password")

# Create/update deck
deck = rememberit.upsert_deck({
    "name": "Python Basics",
    "cards": [
        {"front": "What is a list?", "back": "An ordered collection"},
        {"front": "Create list", "back": "[1, 2, 3]", "back_type": "code"},
    ]
})

# Add more cards
deck.add_card("What is a dict?", "Key-value pairs")

# Sync to AnkiWeb
rememberit.sync()
```
"""


def show_llmtxt() -> str:
    """Show quickstart guide for LLM editing of Anki cards."""
    return """# RememberIt Quickstart for LLMs

## Create Styled Cards (Default)

```python
import rememberit

# Simple styled cards - gradient backgrounds by default
deck = rememberit.upsert_deck({
    "name": "My Deck",
    "cards": [
        {"front": "What is Python?", "back": "A programming language"},
        {"front": "What is a list?", "back": "An ordered collection"},
    ]
})
```

## Add Code Cards

```python
# Syntax-highlighted code
deck = rememberit.upsert_deck({
    "name": "Programming",
    "cards": [
        {
            "front": "Reverse a string in Python",
            "back": "text[::-1]",
            "back_type": "code",
            "back_lang": "python"
        }
    ]
})
```

## Working with Existing Decks

```python
# Get deck by name (subscriptable)
deck = rememberit.decks["Python Basics"]

# Add cards directly to deck
card = deck.add_card("New question?", "New answer")  # Returns Card object

# Update existing card
card.update(back="Updated answer", back_theme="purple")
```

## Card Types & Options

**Types:**
- **(default)**: Styled gradient card - just omit the type
- `"code"`: Syntax-highlighted code block
- `"plain"`: Plain text, no styling

**Themes** (for styled cards):
`random` (default), `gradient`, `dark`, `light`, `blue`, `purple`, `green`, `orange`

**Languages** (for code):
`python`, `javascript`, `typescript`, `html`, `css`, `sql`, `bash`, `json`, `yaml`,
`rust`, `go`, `java`, `c`, `cpp`, `swift`, `kotlin`, `ruby`, `php`

## Configuration

```python
rememberit.auto_sync = False  # Disable auto-sync on decks()
```

## Quick Reference

```python
# Access
rememberit.decks["DeckName"]  # Get by name
deck.cards[0]                  # Get first card
deck.cards["Question text"]    # Fuzzy search

# Add
deck.add_card(front, back)     # Simple (returns Card)
deck.add_card(front, back, back_type="code")  # Code card

# Update
card.update(back="New")        # Styled (default)
card.update(back="x=1", back_type="code")  # Code

# Bulk operations
rememberit.upsert_deck(data)   # Add/update many cards
```
"""


def show_examples() -> str:
    """Show example card formats for different types."""
    return """# RememberIt Card Examples

## 1. Styled Card (Default - No Type Needed)
```json
{"front": "What is Python?", "back": "A programming language"}
```
Creates a beautiful gradient card automatically!

## 2. Code Answer
```json
{
    "front": "Write a function to add two numbers",
    "back": "def add(a, b):\\n    return a + b",
    "back_type": "code",
    "back_lang": "python"
}
```

## 3. Code Question and Answer
```json
{
    "front": "def mystery(n):\\n    return n * 2",
    "front_type": "code",
    "front_lang": "python",
    "back": "Doubles the input number"
}
```

## 4. Themed Styled Card
```json
{
    "front": "Important concept",
    "front_theme": "purple",
    "back": "The explanation",
    "back_theme": "dark"
}
```

## 5. Plain Text (No Styling)
```json
{
    "front": "Simple question",
    "front_type": "plain",
    "back": "Simple answer",
    "back_type": "plain"
}
```

## Complete Deck Example
```python
import rememberit

deck = rememberit.upsert_deck({
    "name": "Mixed Cards",
    "cards": [
        # Styled (default)
        {"front": "What is REST?", "back": "Representational State Transfer"},

        # Code
        {"front": "HTTP GET", "back": "GET /api/users", "back_type": "code"},

        # Themed
        {"front": "Key Concept", "back": "Important!", "front_theme": "purple"},

        # Plain
        {"front": "Note", "back": "Plain text", "back_type": "plain"}
    ]
})
```
"""


# All tools that can be registered with solveit
TOOLS = [
    list_decks,
    list_card_types,
    get_deck,
    deck_as_dict,
    upsert_deck,
    add_card,
    add_code_card,
    add_cards,
    update_card,
    create_deck,
    delete_deck,
    sync_anki,
    show_help,
    show_llmtxt,
    show_examples,
]


def tools_registered() -> bool:
    """Check if rememberit tools have been registered with solveit.

    Returns True if tools are registered and available to the LLM.
    """
    return _TOOLS_REGISTERED


def load_tools(silent: bool = False, force: bool = False) -> None:
    """Load rememberit tools into solveit dialog.

    Registers tools with the LLM via add_msg + mk_toollist.
    Tools are namespaced as rememberit_* (e.g. rememberit_add_card).

    Args:
        silent: If True, don't add a message showing tool list.
        force: If True, re-register even if already registered.

    Returns:
        dict with keys: solveit (bool), registered (bool), tools (list[str])
    """
    global _TOOLS_REGISTERED
    in_solveit = is_solveit()

    if in_solveit and (not _TOOLS_REGISTERED or force):
        from dialoghelper import add_msg, mk_toollist  # type: ignore[attr-defined]

        # Namespace tools with rememberit_ prefix
        namespaced_tools = []
        frame = currentframe()
        caller_globals = frame.f_back.f_globals if frame and frame.f_back else {}

        for tool in TOOLS:
            # Create namespaced name
            namespaced_name = f"rememberit_{tool.__name__}"
            # Store original name, set namespaced name for mk_toollist
            tool.__name__ = namespaced_name
            namespaced_tools.append(tool)
            # Inject into caller's globals
            caller_globals[namespaced_name] = tool

        # This is what makes the LLM aware of the tools
        if not silent:
            tools_md = mk_toollist(namespaced_tools)
            add_msg(f"**RememberIt Anki Tools:**\n\n{tools_md}")

        _TOOLS_REGISTERED = True

    # Display status with styled output (unless silent)
    if not silent:
        status_color = "#90EE90" if _TOOLS_REGISTERED else "#ff6b6b"
        status_icon = "✅" if _TOOLS_REGISTERED else "⚪"
        status_text = "Registered" if _TOOLS_REGISTERED else "Not registered"

        env_color = "#90EE90" if in_solveit else "#87CEEB"
        env_icon = "🎯" if in_solveit else "📓"
        env_text = "solve.it" if in_solveit else "Jupyter"

        tool_list = [f"rememberit_{t.__name__}" for t in TOOLS]
        tools_html = "".join(
            f'<div style="color:#d4d4d4;font-size:0.9em;padding:2px 0;">• {tool}</div>'
            for tool in tool_list
        )

        html = f"""
<div style="background:#1F1F1F;border:1px solid #3A3A3A;border-radius:10px;
padding:16px 20px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;
box-shadow:0 4px 12px rgba(0,0,0,0.15);">

<div style="color:#F5F5F5;font-weight:600;font-size:1.1em;margin-bottom:12px;">
🔧 RememberIt Tools</div>

<div style="display:flex;gap:12px;margin-bottom:16px;">
<span style="background:#1a2e1a;color:{status_color};padding:4px 10px;
border-radius:6px;font-size:0.85em;">{status_icon} {status_text}</span>
<span style="background:#1a2a3a;color:{env_color};padding:4px 10px;
border-radius:6px;font-size:0.85em;">{env_icon} {env_text}</span>
</div>

<div style="color:#d4d4d4;font-size:0.95em;margin-bottom:12px;">
{len(tool_list)} tools available:
</div>

<div style="margin-bottom:12px;">
{tools_html}
</div>

<div style="color:#888;font-size:0.85em;">
Run <code style="background:#272822;color:#f8f8f2;padding:2px 6px;
border-radius:4px;font-family:monospace;">rememberit_show_help()</code>
for API reference
</div>

</div>"""
        _styled_html(html)


def _styled_html(html: str) -> None:
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


def tools_info() -> None:  # noqa: E501
    """Display available rememberit tools (works in any Jupyter context)."""
    registered = _TOOLS_REGISTERED
    in_solveit = is_solveit()

    status_color = "#90EE90" if registered else "#ff6b6b"
    status_bg = "#1a2e1a" if registered else "#2a1a1a"
    status_icon = "✅" if registered else "⚪"
    status_text = "Registered" if registered else "Not registered"

    ctx_color = "#90EE90" if in_solveit else "#87CEEB"
    ctx_icon = "🎯" if in_solveit else "📓"
    ctx_text = "Solveit" if in_solveit else "Jupyter"

    cs = (
        "background:#272822;color:#f8f8f2;padding:2px 6px;"
        "border-radius:4px;font-family:'Fira Code',monospace;font-size:0.85em"
    )
    td = "padding:6px 12px;border:1px solid #444"
    th = "padding:8px 12px;border:1px solid #444;color:#f8f8f2;text-align:left"

    tools = [
        ("list_decks()", "List all decks with card counts"),
        ("get_deck(name)", "Get deck cards as JSON"),
        ("add_card(deck, front, back)", "Add single flashcard"),
        ("add_cards(deck, json)", "Add multiple cards from JSON"),
        ("update_card(deck, front, ...)", "Update existing card"),
        ("create_deck(name)", "Create new deck"),
        ("delete_deck(name)", "Delete deck"),
        ("sync_anki()", "Sync with AnkiWeb"),
    ]
    rows = "\n".join(
        f'<tr><td style="{td}"><code style="{cs}">{t}</code></td><td style="{td}">{d}</td></tr>'
        for t, d in tools
    )

    html = f"""
<div style="background:#1F1F1F;border:1px solid #3A3A3A;border-radius:10px;
padding:16px 20px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;
box-shadow:0 4px 12px rgba(0,0,0,0.15);">
<div style="color:#F5F5F5;font-weight:600;font-size:1.1em;margin-bottom:12px;">
🃏 RememberIt Tools</div>
<div style="display:flex;gap:12px;margin-bottom:16px;">
<span style="background:{status_bg};color:{status_color};padding:4px 10px;
border-radius:6px;font-size:0.85em">{status_icon} {status_text}</span>
<span style="background:#1a2a3a;color:{ctx_color};padding:4px 10px;
border-radius:6px;font-size:0.85em">{ctx_icon} {ctx_text}</span>
</div>
<table style="border-collapse:collapse;width:100%;margin-bottom:16px;">
<thead><tr style="background:#272822;">
<th style="{th}">Tool</th><th style="{th}">Description</th>
</tr></thead>
<tbody style="color:#d4d4d4;">{rows}</tbody>
</table>
<div style="color:#888;font-size:0.8em;">
<code style="{cs}">rememberit.setup()</code> to auto-register in solveit
</div>
</div>"""
    _styled_html(html)
