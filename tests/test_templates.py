"""Tests for rememberit.templates module."""

from __future__ import annotations

import pytest


class TestBuiltinTemplates:
    """Tests for builtin template constants."""

    def test_builtin_templates_exist(self) -> None:
        from rememberit.templates import BUILTIN_TEMPLATES

        assert len(BUILTIN_TEMPLATES) > 0
        assert "code" in BUILTIN_TEMPLATES
        assert "gradient" in BUILTIN_TEMPLATES

    def test_builtin_templates_have_content(self) -> None:
        from rememberit.templates import BUILTIN_TEMPLATES

        for name, content in BUILTIN_TEMPLATES.items():
            assert isinstance(content, str), f"{name} template is not a string"
            assert "{content}" in content, f"{name} template missing {{content}} placeholder"


class TestListTemplates:
    """Tests for list_templates function."""

    def test_returns_dict(self) -> None:
        from rememberit.templates import list_templates

        result = list_templates()
        assert isinstance(result, dict)

    def test_contains_builtin_templates(self) -> None:
        from rememberit.templates import list_templates

        result = list_templates()
        assert "code" in result
        assert "gradient" in result
        assert result["code"] == "builtin"


class TestGetTemplate:
    """Tests for get_template function."""

    def test_get_builtin_template(self) -> None:
        from rememberit.templates import get_template

        result = get_template("code")
        assert result is not None
        assert "{content}" in result

    def test_get_nonexistent_template(self) -> None:
        from rememberit.templates import get_template

        result = get_template("nonexistent_template_xyz")
        assert result is None


class TestRenderTemplate:
    """Tests for render_template function."""

    def test_render_code_template(self) -> None:
        from rememberit.templates import render_template

        result = render_template("code", content="print('hello')")
        assert isinstance(result, str)
        assert "print" in result

    def test_render_gradient_template(self) -> None:
        from rememberit.templates import render_template

        result = render_template("gradient", content="Test content")
        assert isinstance(result, str)
        assert "Test content" in result

    def test_render_nonexistent_template(self) -> None:
        from rememberit.templates import render_template

        with pytest.raises(ValueError):
            render_template("nonexistent_xyz", content="test")

    def test_render_escapes_html(self) -> None:
        from rememberit.templates import render_template

        result = render_template("plain", content="<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestSaveAndDeleteTemplate:
    """Tests for save_template and delete_template functions."""

    def test_save_and_get_custom_template(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import templates

        monkeypatch.setattr(templates, "TEMPLATES_DIR", tmp_path)

        templates.save_template("mytest", "<div>{content}</div>")

        result = templates.get_template("mytest")
        assert result == "<div>{content}</div>"

    def test_save_template_requires_placeholder(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        from rememberit import templates

        monkeypatch.setattr(templates, "TEMPLATES_DIR", tmp_path)

        with pytest.raises(ValueError):
            templates.save_template("invalid", "<div>no placeholder</div>")

    def test_delete_custom_template(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import templates

        monkeypatch.setattr(templates, "TEMPLATES_DIR", tmp_path)

        templates.save_template("todelete", "<p>{content}</p>")
        assert templates.get_template("todelete") is not None

        result = templates.delete_template("todelete")
        assert result is True
        assert templates.get_template("todelete") is None

    def test_delete_nonexistent_template_returns_false(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        from rememberit import templates

        monkeypatch.setattr(templates, "TEMPLATES_DIR", tmp_path)

        result = templates.delete_template("nonexistent")
        assert result is False


class TestExportBuiltin:
    """Tests for export_builtin function."""

    def test_export_builtin_template(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import templates

        monkeypatch.setattr(templates, "TEMPLATES_DIR", tmp_path)

        templates.export_builtin("code")

        exported = templates.get_template("code")
        assert exported is not None
        assert "{content}" in exported

    def test_export_nonexistent_builtin(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from rememberit import templates

        monkeypatch.setattr(templates, "TEMPLATES_DIR", tmp_path)

        with pytest.raises(ValueError):
            templates.export_builtin("nonexistent_builtin_xyz")


class TestTemplateInfo:
    """Tests for template_info function."""

    def test_template_info_returns_dict(self) -> None:
        from rememberit.templates import template_info

        result = template_info()
        assert isinstance(result, dict)
        assert "templates_dir" in result
        assert "builtin_count" in result
        assert "custom_count" in result
        assert "templates" in result

    def test_template_info_counts(self) -> None:
        from rememberit.templates import BUILTIN_TEMPLATES, template_info

        result = template_info()
        assert result["builtin_count"] == len(BUILTIN_TEMPLATES)
