from __future__ import annotations

from collections.abc import Iterable, Mapping


def decks_markdown_table(flat_decks: Iterable[Mapping[str, object]]) -> str:
    """
    Build a simple Markdown table for decks.
    Expected keys: id, path, new, learn, review, total, total_incl_children.
    """
    headers = ["id", "path", "new", "learn", "review", "total", "total_incl_children"]
    lines = [
        "|" + "|".join(headers) + "|",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in flat_decks:
        lines.append("|" + "|".join(str(row.get(col, "")) for col in headers) + "|")
    return "\n".join(lines)
