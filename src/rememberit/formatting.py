from __future__ import annotations

import inspect
import random
import re
import textwrap
from collections.abc import Callable, Iterable, Mapping
from typing import Any

_PYGMENTS_AVAILABLE = False
try:
    from pygments import highlight  # type: ignore[import-untyped]
    from pygments.formatters import HtmlFormatter  # type: ignore[import-untyped]
    from pygments.lexers import get_lexer_by_name  # type: ignore[import-untyped]

    _PYGMENTS_AVAILABLE = True
except ImportError:
    pass


SUPPORTED_LANGUAGES = [
    "python",
    "javascript",
    "typescript",
    "html",
    "css",
    "sql",
    "bash",
    "shell",
    "json",
    "yaml",
    "rust",
    "go",
    "java",
    "c",
    "cpp",
    "swift",
    "kotlin",
    "ruby",
    "php",
    "r",
    "scala",
    "haskell",
    "lua",
    "perl",
    "markdown",
]


def extract_source(func: Callable[..., Any]) -> str:
    """
    Extract source code from a function or callable object.

    Args:
        func: A function, method, or other callable

    Returns:
        The dedented source code as a string

    Raises:
        TypeError: If source cannot be extracted
    """
    try:
        source = inspect.getsource(func)
        return textwrap.dedent(source)
    except (TypeError, OSError) as e:
        raise TypeError(f"Cannot extract source from {func}: {e}") from e


def format_code(code: str | Callable[..., Any], language: str = "python") -> str:
    """
    Format code as HTML with syntax highlighting for Anki cards.

    Uses Pygments if available, otherwise falls back to a styled <pre> block.
    Can accept either a string or a function object (source will be extracted).
    Includes data attributes for reverse parsing.

    Args:
        code: Source code string OR a function/callable to extract source from
        language: Programming language for syntax highlighting (default: python)

    Returns:
        HTML string with inline styles for Anki compatibility

    Example:
        >>> def add(a, b):
        ...     return a + b
        >>> html = format_code(add)  # Extracts source automatically
    """
    if callable(code) and not isinstance(code, str):
        code = extract_source(code)

    # Store original for data attribute
    escaped_content = (
        code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )

    if _PYGMENTS_AVAILABLE:
        try:
            lexer = get_lexer_by_name(language, stripall=True)
            formatter = HtmlFormatter(
                noclasses=True,
                style="monokai",
                nowrap=False,
                prestyles=(
                    "background:#272822; color:#f8f8f2; padding:16px 20px; "
                    "border-radius:12px; font-family:'Fira Code','SF Mono',Consolas,"
                    "'Liberation Mono',Menlo,monospace; font-size:18px; "
                    "line-height:1.6; white-space:pre-wrap; word-wrap:break-word;"
                ),
            )
            highlighted: str = highlight(code, lexer, formatter)
            return (
                f'<div data-ri-type="code" data-ri-lang="{language}">'
                f'<div data-ri-content="{escaped_content}"></div>'
                f"{highlighted}</div>"
            )
        except Exception:
            pass

    return (
        f'<div data-ri-type="code" data-ri-lang="{language}">'
        f'<div data-ri-content="{escaped_content}"></div>'
        f'<pre style="background:#272822; color:#f8f8f2; padding:16px 20px; '
        f"border-radius:12px; font-family:'Fira Code','SF Mono',Consolas,"
        f"'Liberation Mono',Menlo,monospace; font-size:18px; line-height:1.6; "
        f'white-space:pre-wrap; word-wrap:break-word;">{escaped_content}</pre></div>'
    )


CARD_THEMES = {
    "gradient": {
        "bg": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "color": "#ffffff",
        "shadow": "0 10px 40px rgba(102, 126, 234, 0.3)",
    },
    "dark": {
        "bg": "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
        "color": "#f0f0f0",
        "shadow": "0 10px 40px rgba(0, 0, 0, 0.4)",
    },
    "light": {
        "bg": "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
        "color": "#2d3748",
        "shadow": "0 10px 40px rgba(0, 0, 0, 0.1)",
    },
    "blue": {
        "bg": "linear-gradient(135deg, #0093E9 0%, #80D0C7 100%)",
        "color": "#ffffff",
        "shadow": "0 10px 40px rgba(0, 147, 233, 0.3)",
    },
    "purple": {
        "bg": "linear-gradient(135deg, #8B5CF6 0%, #D946EF 100%)",
        "color": "#ffffff",
        "shadow": "0 10px 40px rgba(139, 92, 246, 0.3)",
    },
    "green": {
        "bg": "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)",
        "color": "#ffffff",
        "shadow": "0 10px 40px rgba(17, 153, 142, 0.3)",
    },
    "orange": {
        "bg": "linear-gradient(135deg, #F97316 0%, #FBBF24 100%)",
        "color": "#ffffff",
        "shadow": "0 10px 40px rgba(249, 115, 22, 0.3)",
    },
}


def format_question(text: str, theme: str = "random") -> str:
    """
    Format a question as a styled HTML card for Anki.

    Creates a visually appealing question card with centered text,
    gradient background, and large readable font.
    Includes data attributes for reverse parsing.

    Args:
        text: The question text
        theme: Visual theme - "random" (default), "gradient", "dark", "light",
               "blue", "purple", "green", "orange"

    Returns:
        HTML string with styled question card
    """
    escaped = (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )

    actual_theme = theme
    if actual_theme == "random":
        actual_theme = random.choice(list(CARD_THEMES.keys()))

    t = CARD_THEMES.get(actual_theme, CARD_THEMES["gradient"])

    wrapper_open = f'<div data-ri-type="card" data-ri-theme="{actual_theme}">'
    content_div = f'<div data-ri-content="{escaped}"></div>'
    return f"""{wrapper_open}{content_div}<div style="
display: flex;
align-items: center;
justify-content: center;
min-height: 200px;
padding: 40px 30px;
background: {t["bg"]};
border-radius: 16px;
box-shadow: {t["shadow"]};
">
<div style="
color: {t["color"]};
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
font-size: 28px;
font-weight: 600;
text-align: center;
line-height: 1.4;
text-shadow: 0 2px 4px rgba(0,0,0,0.1);
">{escaped}</div>
</div></div>"""


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


def parse_card_field(html: str) -> dict[str, str]:
    """
    Parse a card field HTML back to plain text and metadata.

    Extracts data attributes added by format_code and format_question.

    Args:
        html: HTML string from a card field

    Returns:
        Dict with keys: content, type, and optionally lang/theme
        - For code: {content, type="code", lang}
        - For card: {content, type="card", theme}
        - For plain/unknown: {content, type="plain"}
    """
    # Check for data-ri-type attribute
    type_match = re.search(r'data-ri-type="([^"]+)"', html)
    if not type_match:
        # Plain text or unknown format - strip all HTML tags
        plain = re.sub(r"<[^>]+>", "", html)
        plain = (
            plain.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )
        return {"content": plain.strip(), "type": "plain"}

    field_type = type_match.group(1)

    # Extract content from data-ri-content attribute
    content_match = re.search(r'data-ri-content="([^"]*)"', html)
    if content_match:
        content = content_match.group(1)
        # Unescape HTML entities
        content = (
            content.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )
    else:
        # Fallback: strip HTML
        content = re.sub(r"<[^>]+>", "", html).strip()

    result: dict[str, str] = {"content": content, "type": field_type}

    if field_type == "code":
        lang_match = re.search(r'data-ri-lang="([^"]+)"', html)
        if lang_match:
            result["lang"] = lang_match.group(1)

    elif field_type == "card":
        theme_match = re.search(r'data-ri-theme="([^"]+)"', html)
        if theme_match:
            result["theme"] = theme_match.group(1)

    return result
