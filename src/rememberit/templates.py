"""Card templates for RememberIt.

Templates are stored as .template files containing HTML with placeholders:
- {content} - The card content (required)
- {language} - Programming language for code templates

Built-in templates: code, gradient, dark, light, blue, purple, green, orange
Custom templates: ~/.rememberit/templates/<name>.template
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path.home() / ".rememberit" / "templates"

BUILTIN_TEMPLATES: dict[str, str] = {
    "code": """<div style="
background:#272822; color:#f8f8f2; padding:16px 20px;
border-radius:12px; font-family:'Fira Code','SF Mono',Consolas,
'Liberation Mono',Menlo,monospace; font-size:18px;
line-height:1.6; white-space:pre-wrap; word-wrap:break-word;
">{content}</div>""",
    "gradient": """<div style="
display: flex; align-items: center; justify-content: center;
min-height: 200px; padding: 40px 30px;
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
border-radius: 16px; box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
">
<div style="
color: #ffffff;
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
font-size: 28px; font-weight: 600; text-align: center;
line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
">{content}</div>
</div>""",
    "dark": """<div style="
display: flex; align-items: center; justify-content: center;
min-height: 200px; padding: 40px 30px;
background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
border-radius: 16px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
">
<div style="
color: #f0f0f0;
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
font-size: 28px; font-weight: 600; text-align: center;
line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
">{content}</div>
</div>""",
    "light": """<div style="
display: flex; align-items: center; justify-content: center;
min-height: 200px; padding: 40px 30px;
background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
border-radius: 16px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
">
<div style="
color: #2d3748;
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
font-size: 28px; font-weight: 600; text-align: center;
line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
">{content}</div>
</div>""",
    "blue": """<div style="
display: flex; align-items: center; justify-content: center;
min-height: 200px; padding: 40px 30px;
background: linear-gradient(135deg, #0093E9 0%, #80D0C7 100%);
border-radius: 16px; box-shadow: 0 10px 40px rgba(0, 147, 233, 0.3);
">
<div style="
color: #ffffff;
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
font-size: 28px; font-weight: 600; text-align: center;
line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
">{content}</div>
</div>""",
    "purple": """<div style="
display: flex; align-items: center; justify-content: center;
min-height: 200px; padding: 40px 30px;
background: linear-gradient(135deg, #8B5CF6 0%, #D946EF 100%);
border-radius: 16px; box-shadow: 0 10px 40px rgba(139, 92, 246, 0.3);
">
<div style="
color: #ffffff;
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
font-size: 28px; font-weight: 600; text-align: center;
line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
">{content}</div>
</div>""",
    "green": """<div style="
display: flex; align-items: center; justify-content: center;
min-height: 200px; padding: 40px 30px;
background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
border-radius: 16px; box-shadow: 0 10px 40px rgba(17, 153, 142, 0.3);
">
<div style="
color: #ffffff;
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
font-size: 28px; font-weight: 600; text-align: center;
line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
">{content}</div>
</div>""",
    "orange": """<div style="
display: flex; align-items: center; justify-content: center;
min-height: 200px; padding: 40px 30px;
background: linear-gradient(135deg, #F97316 0%, #FBBF24 100%);
border-radius: 16px; box-shadow: 0 10px 40px rgba(249, 115, 22, 0.3);
">
<div style="
color: #ffffff;
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
font-size: 28px; font-weight: 600; text-align: center;
line-height: 1.4; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
">{content}</div>
</div>""",
    "plain": "{content}",
}


def _ensure_templates_dir() -> Path:
    """Ensure ~/.rememberit/templates exists."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return TEMPLATES_DIR


def list_templates() -> dict[str, str]:
    """List all available templates (builtin + custom).

    Returns:
        Dict mapping template name to source ("builtin" or file path)
    """
    result: dict[str, str] = {name: "builtin" for name in BUILTIN_TEMPLATES}

    if TEMPLATES_DIR.exists():
        for f in TEMPLATES_DIR.glob("*.template"):
            result[f.stem] = str(f)

    return result


def get_template(name: str) -> str | None:
    """Get a template by name.

    Checks custom templates first, then builtin.

    Args:
        name: Template name (without .template extension)

    Returns:
        Template HTML string or None if not found
    """
    custom_path = TEMPLATES_DIR / f"{name}.template"
    if custom_path.exists():
        return custom_path.read_text(encoding="utf-8")

    return BUILTIN_TEMPLATES.get(name)


def save_template(name: str, html: str) -> Path:
    """Save a custom template.

    Args:
        name: Template name (will be saved as {name}.template)
        html: HTML template with {content} placeholder

    Returns:
        Path to saved template file
    """
    if "{content}" not in html:
        raise ValueError("Template must contain {content} placeholder")

    _ensure_templates_dir()
    path = TEMPLATES_DIR / f"{name}.template"
    path.write_text(html, encoding="utf-8")
    return path


def delete_template(name: str) -> bool:
    """Delete a custom template.

    Args:
        name: Template name

    Returns:
        True if deleted, False if not found (builtin templates cannot be deleted)
    """
    path = TEMPLATES_DIR / f"{name}.template"
    if path.exists():
        path.unlink()
        return True
    return False


def export_builtin(name: str) -> Path:
    """Export a builtin template to the custom templates dir for editing.

    Args:
        name: Builtin template name

    Returns:
        Path to exported template file
    """
    if name not in BUILTIN_TEMPLATES:
        raise ValueError(f"Unknown builtin template: {name}")

    return save_template(name, BUILTIN_TEMPLATES[name])


def render_template(name: str, content: str, **kwargs: Any) -> str:
    """Render a template with content.

    Args:
        name: Template name
        content: Content to insert
        **kwargs: Additional format arguments (e.g., language for code)

    Returns:
        Rendered HTML string
    """
    template = get_template(name)
    if template is None:
        raise ValueError(f"Template not found: {name}")

    escaped = (
        content.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return template.format(content=escaped, **kwargs)


def show_templates() -> None:
    """Display all available templates with previews."""
    try:
        from IPython.display import HTML, display

        has_ipython = True
    except ImportError:
        has_ipython = False

    templates = list_templates()

    if has_ipython:
        rows = []
        for name, source in sorted(templates.items()):
            source_badge = (
                "<span style='background:#4CAF50;color:white;padding:2px 8px;"
                "border-radius:4px;font-size:0.8em;'>builtin</span>"
                if source == "builtin"
                else "<span style='background:#2196F3;color:white;padding:2px 8px;"
                "border-radius:4px;font-size:0.8em;'>custom</span>"
            )
            preview = render_template(name, f"Example {name} card")
            rows.append(
                f"<tr><td style='padding:12px;border:1px solid #444;vertical-align:top;'>"
                f"<b>{name}</b><br/>{source_badge}</td>"
                f"<td style='padding:12px;border:1px solid #444;'>{preview}</td></tr>"
            )

        html = f"""
<div style="background:#1F1F1F;border:1px solid #3A3A3A;border-radius:12px;
padding:20px 24px;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;">
<div style="color:#F5F5F5;font-weight:700;font-size:1.3em;margin-bottom:16px;">
Card Templates</div>
<table style="border-collapse:collapse;width:100%;">
<thead><tr style="background:#272822;">
<th style="padding:12px;border:1px solid #444;color:#f8f8f2;text-align:left;">Name</th>
<th style="padding:12px;border:1px solid #444;color:#f8f8f2;text-align:left;">Preview</th>
</tr></thead>
<tbody style="color:#d4d4d4;">{"".join(rows)}</tbody></table>
<div style="color:#888;font-size:0.85em;margin-top:16px;">
Custom templates: <code style="background:#272822;color:#f8f8f2;padding:2px 6px;
border-radius:4px;">~/.rememberit/templates/</code>
</div>
</div>"""
        display(HTML(html))  # type: ignore[no-untyped-call]
    else:
        print("Available templates:")
        for name, source in sorted(templates.items()):
            print(f"  {name} ({source})")


def template_info() -> dict[str, Any]:
    """Get template system info as a dict.

    Returns:
        Dict with templates_dir, builtin_count, custom_count, templates
    """
    templates = list_templates()
    custom_count = sum(1 for s in templates.values() if s != "builtin")
    return {
        "templates_dir": str(TEMPLATES_DIR),
        "builtin_count": len(BUILTIN_TEMPLATES),
        "custom_count": custom_count,
        "templates": templates,
    }
