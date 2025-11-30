"""Example code snippets and cards for rememberit.

Usage:
    import rememberit
    rememberit.examples.code()       # Show all code examples
    rememberit.examples.questions()  # Show styled question examples
    rememberit.examples.images()     # Show an image example (data URI)
    rememberit.examples.all()        # Show everything
"""

from __future__ import annotations

from pathlib import Path

from .formatting import SUPPORTED_LANGUAGES, format_code, format_image, format_question

CODE_EXAMPLES: dict[str, str] = {
    "python": '''def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)''',
    "javascript": """function debounce(fn, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
}""",
    "typescript": """interface User {
    id: number;
    name: string;
    email: string;
}

const getUser = async (id: number): Promise<User> => {
    const response = await fetch(`/api/users/${id}`);
    return response.json();
};""",
    "html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Hello World</title>
</head>
<body>
    <h1>Welcome!</h1>
</body>
</html>""",
    "css": """.card {
    display: flex;
    flex-direction: column;
    padding: 1.5rem;
    border-radius: 12px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}""",
    "sql": """SELECT
    users.name,
    COUNT(orders.id) AS order_count,
    SUM(orders.total) AS total_spent
FROM users
LEFT JOIN orders ON users.id = orders.user_id
WHERE orders.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY users.id
HAVING order_count > 5
ORDER BY total_spent DESC;""",
    "bash": """#!/bin/bash
# Find and replace in all Python files
find . -name "*.py" -type f | while read file; do
    sed -i '' 's/old_function/new_function/g' "$file"
    echo "Processed: $file"
done""",
    "json": """{
    "name": "rememberit",
    "version": "0.1.0",
    "dependencies": {
        "pygments": "^2.17.0"
    },
    "scripts": {
        "test": "pytest"
    }
}""",
    "yaml": """name: CI Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest --cov""",
    "rust": """fn main() {
    let numbers: Vec<i32> = (1..=10).collect();
    let sum: i32 = numbers.iter()
        .filter(|&x| x % 2 == 0)
        .sum();
    println!("Sum of evens: {}", sum);
}""",
    "go": """package main

import "fmt"

func main() {
    ch := make(chan int, 5)
    go func() {
        for i := 0; i < 5; i++ {
            ch <- i * i
        }
        close(ch)
    }()
    for n := range ch {
        fmt.Println(n)
    }
}""",
    "swift": """struct ContentView: View {
    @State private var count = 0

    var body: some View {
        VStack {
            Text("Count: \\(count)")
                .font(.largeTitle)
            Button("Increment") {
                count += 1
            }
        }
    }
}""",
}

QUESTION_THEMES = ["gradient", "dark", "light", "blue", "purple", "green", "orange"]

SAMPLE_QUESTIONS = [
    "What is the time complexity of binary search?",
    "How does Python's garbage collector work?",
    "What is the difference between let and const?",
    "Explain the CAP theorem",
]


def _styled_html(html: str) -> None:
    """Display styled HTML in notebook, falls back to print."""
    try:
        from IPython.display import HTML, display

        display(HTML(html))  # type: ignore[no-untyped-call]
    except ImportError:
        print("[HTML output - run in Jupyter to see styled version]")


def code() -> None:
    """Display syntax-highlighted code examples for all supported languages."""
    _styled_html("<h2>📝 Code Formatting Examples</h2>")
    _styled_html(f"<p><b>Supported languages:</b> {', '.join(SUPPORTED_LANGUAGES)}</p>")
    _styled_html("<hr/>")

    for lang, snippet in CODE_EXAMPLES.items():
        _styled_html(f"<h3>{lang}</h3>")
        _styled_html(format_code(snippet, language=lang))
        _styled_html("<br/>")


def questions() -> None:
    """Display styled question card examples with different themes."""
    _styled_html("<h2>🎴 Question Card Themes</h2>")
    _styled_html("<p>Use <code>front_type='card'</code> with optional <code>front_theme</code></p>")
    _styled_html("<hr/>")

    for i, theme in enumerate(QUESTION_THEMES):
        question = SAMPLE_QUESTIONS[i % len(SAMPLE_QUESTIONS)]
        _styled_html(f"<h3>Theme: {theme}</h3>")
        _styled_html(format_question(question, theme=theme))
        _styled_html("<br/>")


def all() -> None:
    """Display all examples: code formatting and question cards."""
    code()
    _styled_html("<hr style='margin: 40px 0;'/>")
    questions()
    _styled_html("<hr style='margin: 40px 0;'/>")
    images()


def images() -> None:
    """Display minimal image embed examples (data URI)."""
    _styled_html("<h2>🖼 Image Embed Examples</h2>")
    _styled_html(
        "<p>Pass a file path, bytes, base64, or any object with "
        "<code>_repr_png_</code>/<code>_repr_jpeg_</code> (e.g., tinyviz graph).</p>"
    )
    import base64

    # Example 1: tiny transparent PNG (base64)
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAnsB9rx1Ns0AAAAASUVORK5CYII="  # noqa: E501
    png_bytes = base64.b64decode(tiny_png_b64)
    html = format_image(png_bytes, alt="1x1 transparent PNG", max_bytes=None)
    _styled_html("<h3>Transparent pixel (base64)</h3>")
    _styled_html(html)

    # Example 2: bundled photo (image/pickles.jpg)
    pickles_path = _find_pickles_image()
    if pickles_path:
        _styled_html("<h3>Bundled example (pickles.jpg)</h3>")
        _styled_html(format_image(pickles_path, alt="Pickles the dog"))
    else:
        _styled_html("<p><i>Pickles image not found.</i></p>")


def deck_example() -> dict[str, object]:
    """
    Return an example deck dict with code and styled question cards.

    This can be passed directly to rememberit.upsert_deck().
    """
    return {
        "name": "Python Examples",
        "cards": [
            {
                "front": "What is a list comprehension?",
                "front_type": "card",
                "front_theme": "gradient",
                "back": "[x**2 for x in range(10)]",
                "back_type": "code",
                "back_lang": "python",
            },
            {
                "front": "Write a function to check if a number is prime",
                "front_type": "card",
                "front_theme": "purple",
                "back": """def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True""",
                "back_type": "code",
                "back_lang": "python",
            },
            {
                "front": "How do you create a dictionary from two lists?",
                "front_type": "card",
                "front_theme": "blue",
                "back": """keys = ['a', 'b', 'c']
values = [1, 2, 3]
result = dict(zip(keys, values))
# {'a': 1, 'b': 2, 'c': 3}""",
                "back_type": "code",
                "back_lang": "python",
            },
        ],
    }


def _find_pickles_image() -> Path | None:
    """Locate bundled pickles.jpg (installed or editable)."""
    candidates = [
        Path(__file__).resolve().parent.parent / "image" / "pickles.jpg",
        Path(__file__).resolve().parent / "image" / "pickles.jpg",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None
