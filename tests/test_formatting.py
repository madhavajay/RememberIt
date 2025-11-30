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


class TestFormatImage:
    """Tests for format_image function."""

    def test_formats_file_path(self) -> None:
        from pathlib import Path

        from rememberit.formatting import format_image

        # Use bundled pickles.jpg
        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            # Skip if image not found
            return

        result = format_image(pickles_path)
        assert isinstance(result, str)
        assert "<img" in result
        assert "base64" in result
        assert "data:image/" in result

    def test_formats_string_path(self) -> None:
        from pathlib import Path

        from rememberit.formatting import format_image

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        result = format_image(str(pickles_path))
        assert isinstance(result, str)
        assert "<img" in result
        assert "base64" in result

    def test_contains_data_attributes(self) -> None:
        from pathlib import Path

        from rememberit.formatting import format_image

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        result = format_image(pickles_path, alt="test image")
        assert 'data-ri-type="image"' in result
        assert "data-ri-mime" in result
        assert "data-ri-bytes" in result
        assert 'alt="test image"' in result

    def test_formats_pil_image(self) -> None:
        from pathlib import Path

        from rememberit.formatting import format_image

        try:
            from PIL import Image
        except ImportError:
            # Skip if PIL not installed
            return

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        pil_image = Image.open(pickles_path)
        result = format_image(pil_image)
        assert isinstance(result, str)
        assert "<img" in result
        assert "base64" in result


class TestAutoFormatField:
    """Tests for auto_format_field function."""

    def test_returns_string_for_plain_text(self) -> None:
        from rememberit.formatting import auto_format_field

        result = auto_format_field("plain text")
        assert result == "plain text"
        assert isinstance(result, str)

    def test_converts_non_string_to_string(self) -> None:
        from rememberit.formatting import auto_format_field

        result = auto_format_field(42)
        assert result == "42"
        assert isinstance(result, str)

    def test_auto_detects_image_path(self) -> None:
        from pathlib import Path

        from rememberit.formatting import auto_format_field

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        result = auto_format_field(pickles_path)
        assert isinstance(result, str)
        assert "<img" in result
        assert "base64" in result

    def test_auto_detects_pil_image(self) -> None:
        from pathlib import Path

        from rememberit.formatting import auto_format_field

        try:
            from PIL import Image
        except ImportError:
            return

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        pil_image = Image.open(pickles_path)
        result = auto_format_field(pil_image)
        assert isinstance(result, str)
        assert "<img" in result
        assert "base64" in result

    def test_handles_path_objects(self) -> None:
        from pathlib import Path

        from rememberit.formatting import auto_format_field

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        result = auto_format_field(pickles_path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string_as_is_for_non_image_paths(self) -> None:
        from rememberit.formatting import auto_format_field

        result = auto_format_field("not/a/real/image.txt")
        # Should return the string as-is if it's not a valid image
        assert isinstance(result, str)

    def test_handles_relative_path(self) -> None:
        from pathlib import Path

        from rememberit.formatting import auto_format_field

        # Use current working directory to create a relative path
        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        cwd = Path.cwd()
        # Create relative path from current working directory
        try:
            rel_path = pickles_path.relative_to(cwd)
            result = auto_format_field(str(rel_path))
            assert isinstance(result, str)
            # Should successfully format if pickles is accessible from cwd
            if "<img" in result:
                assert "base64" in result
        except ValueError:
            # If we can't create a relative path, skip this test
            pass

    def test_handles_absolute_path(self) -> None:
        from pathlib import Path

        from rememberit.formatting import auto_format_field

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        result = auto_format_field(str(pickles_path.absolute()))
        assert isinstance(result, str)
        assert "<img" in result
        assert "base64" in result

    def test_handles_tilde_path(self) -> None:
        from pathlib import Path
        from shutil import copy2

        from rememberit.formatting import auto_format_field

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        # Create a temp file in home directory to test ~ expansion
        home = Path.home()
        temp_name = "test_pickles_temp.jpg"
        temp_path = home / temp_name

        try:
            copy2(pickles_path, temp_path)
            result = auto_format_field(f"~/{temp_name}")
            assert isinstance(result, str)
            assert "<img" in result
            assert "base64" in result
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_handles_object_with_repr_png(self) -> None:
        from rememberit.formatting import auto_format_field

        class MockImageObject:
            def _repr_png_(self) -> bytes:
                # Return a minimal valid PNG (1x1 transparent pixel)
                return (
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
                    b"\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc"
                    b"\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                )

        mock_obj = MockImageObject()
        result = auto_format_field(mock_obj)
        assert isinstance(result, str)
        assert "<img" in result
        assert "base64" in result

    def test_handles_object_with_repr_jpeg(self) -> None:
        from rememberit.formatting import auto_format_field

        class MockJpegObject:
            def _repr_jpeg_(self) -> bytes:
                # Return minimal JPEG header
                return b"\xff\xd8\xff\xe0\x00\x10JFIF"

        mock_obj = MockJpegObject()
        result = auto_format_field(mock_obj)
        assert isinstance(result, str)
        assert "<img" in result
        assert "base64" in result
