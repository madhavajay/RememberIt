"""Tests for rememberit.formatting module."""

from __future__ import annotations


class TestFormatCode:
    """Tests for format_code function."""

    def test_returns_html_string(self) -> None:
        from rememberit.formatting import format_code

        result = format_code("print('hello')", "python")
        assert isinstance(result, str)
        assert "<" in result

    def test_contains_data_attributes(self) -> None:
        from rememberit.formatting import format_code

        result = format_code("print('hello')", "python")
        assert "data-ri-type" in result
        assert "data-ri-content" in result

    def test_python_highlighting(self) -> None:
        from rememberit.formatting import format_code

        result = format_code("def foo(): pass", "python")
        assert "def" in result

    def test_unknown_language_fallback(self) -> None:
        from rememberit.formatting import format_code

        result = format_code("some code", "unknownlang123")
        assert isinstance(result, str)


class TestFormatQuestion:
    """Tests for format_question function."""

    def test_returns_html_string(self) -> None:
        from rememberit.formatting import format_question

        result = format_question("What is Python?")
        assert isinstance(result, str)
        assert "<" in result

    def test_contains_data_attributes(self) -> None:
        from rememberit.formatting import format_question

        result = format_question("Test question", theme="blue")
        assert "data-ri-type" in result
        assert "data-ri-content" in result
        assert "data-ri-theme" in result

    def test_themes(self) -> None:
        from rememberit.formatting import format_question

        themes = ["gradient", "dark", "light", "blue", "purple", "green", "orange"]
        for theme in themes:
            result = format_question("Test", theme=theme)
            assert isinstance(result, str)
            assert len(result) > 50


class TestExtractSource:
    """Tests for extract_source function."""

    def test_extracts_function_source(self) -> None:
        from rememberit.formatting import extract_source

        def sample_func():
            return 42

        result = extract_source(sample_func)
        assert "def sample_func" in result
        assert "return 42" in result

    def test_extracts_lambda_source(self) -> None:
        from rememberit.formatting import extract_source

        fn = lambda x: x * 2  # noqa: E731
        result = extract_source(fn)
        assert "lambda" in result


class TestParseCardField:
    """Tests for parse_card_field function."""

    def test_parses_code_field(self) -> None:
        from rememberit.formatting import format_code, parse_card_field

        html = format_code("print('hello')", "python")
        result = parse_card_field(html)

        assert result["type"] == "code"
        assert result["lang"] == "python"
        assert "print" in result["content"]

    def test_parses_card_field(self) -> None:
        from rememberit.formatting import format_question, parse_card_field

        html = format_question("What is Python?", theme="blue")
        result = parse_card_field(html)

        assert result["type"] == "card"
        assert result["theme"] == "blue"
        assert "What is Python?" in result["content"]

    def test_parses_plain_text(self) -> None:
        from rememberit.formatting import parse_card_field

        result = parse_card_field("Just plain text")

        assert result["type"] == "plain"
        assert result["content"] == "Just plain text"

    def test_returns_dict_structure(self) -> None:
        from rememberit.formatting import parse_card_field

        result = parse_card_field("test")
        assert isinstance(result, dict)
        assert "type" in result
        assert "content" in result


class TestSupportedLanguages:
    """Tests for SUPPORTED_LANGUAGES constant."""

    def test_contains_common_languages(self) -> None:
        from rememberit.formatting import SUPPORTED_LANGUAGES

        expected = ["python", "javascript", "html", "css", "sql", "bash"]
        for lang in expected:
            assert lang in SUPPORTED_LANGUAGES

    def test_is_not_empty(self) -> None:
        from rememberit.formatting import SUPPORTED_LANGUAGES

        assert len(SUPPORTED_LANGUAGES) >= 10
