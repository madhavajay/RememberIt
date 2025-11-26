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
    """List all available Anki decks with their card counts."""
    import rememberit

    collection = rememberit.decks()
    if not collection:
        return "No decks found. Try `rememberit_sync()` first."
    lines = ["| Deck | Cards |", "|------|-------|"]
    for deck in collection:
        lines.append(f"| {deck.path} | {len(deck.cards)} |")
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


def add_card(deck_name: str, front: str, back: str, tags: str = "") -> str:
    """Add a new flashcard to a deck.

    Args:
        deck_name: Name of the deck (created if doesn't exist)
        front: Front side of the card (question)
        back: Back side of the card (answer)
        tags: Optional space-separated tags
    """
    import rememberit

    collection = rememberit.decks()
    deck = collection[deck_name]  # auto-creates if missing
    deck.add_card(front, back, tags)
    return f"✓ Card added to '{deck_name}'"


def add_cards(deck_name: str, cards_json: str) -> str:
    """Add multiple flashcards to a deck from JSON.

    Args:
        deck_name: Name of the deck (created if doesn't exist)
        cards_json: JSON array of cards: [{"front": "...", "back": "...", "tags": "..."}]
    """
    import json

    import rememberit

    cards = json.loads(cards_json)
    if not isinstance(cards, list):
        return "Error: cards_json must be a JSON array"

    collection = rememberit.decks()
    deck = collection[deck_name]

    for card in cards:
        front = card.get("front", "")
        back = card.get("back", "")
        tags = card.get("tags", "")
        if front and back:
            deck.add_card(front, back, tags)

    return f"✓ Added {len(cards)} cards to '{deck_name}'"


def update_card(deck_name: str, card_front: str, new_front: str = "", new_back: str = "") -> str:
    """Update an existing card by matching its front text.

    Args:
        deck_name: Name of the deck containing the card
        card_front: Current front text to find the card
        new_front: New front text (empty = keep current)
        new_back: New back text (empty = keep current)
    """
    import rememberit

    collection = rememberit.decks()
    try:
        deck = collection[deck_name]
        deck.sync()
        card = deck.cards[card_front]
        card.update(front=new_front if new_front else None, back=new_back if new_back else None)
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


# All tools that can be registered with solveit
TOOLS = [
    list_decks,
    get_deck,
    add_card,
    add_cards,
    update_card,
    create_deck,
    delete_deck,
    sync_anki,
]


def tools_registered() -> bool:
    """Check if rememberit tools have been registered with solveit.

    Returns True if tools are registered and available to the LLM.
    """
    return _TOOLS_REGISTERED


def load_tools(silent: bool = False, force: bool = False) -> dict[str, object]:
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

    return {
        "solveit": in_solveit,
        "registered": _TOOLS_REGISTERED,
        "tools": [f"rememberit_{t.__name__}" for t in TOOLS] if not _TOOLS_REGISTERED else [],
    }


def _styled_html(html: str) -> None:
    """Display styled HTML in notebook, falls back to print."""
    try:
        from IPython.display import HTML, display

        display(HTML(html))  # type: ignore[no-untyped-call]
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
