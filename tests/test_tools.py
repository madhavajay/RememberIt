"""Tests for rememberit.tools module."""

from __future__ import annotations

import pytest


class TestToolDefinitions:
    """Tests for tool function definitions."""

    def test_all_tools_have_docstrings(self) -> None:
        from rememberit.tools import TOOLS

        for tool in TOOLS:
            assert tool.__doc__ is not None, f"{tool.__name__} missing docstring"
            assert len(tool.__doc__) > 10, f"{tool.__name__} docstring too short"

    def test_all_tools_have_type_hints(self) -> None:
        from rememberit.tools import TOOLS

        for tool in TOOLS:
            hints = getattr(tool, "__annotations__", {})
            assert "return" in hints, f"{tool.__name__} missing return type hint"

    def test_tools_list_not_empty(self) -> None:
        from rememberit.tools import TOOLS

        assert len(TOOLS) >= 5

    def test_expected_tools_exist(self) -> None:
        from rememberit.tools import TOOLS

        tool_names = {t.__name__ for t in TOOLS}
        expected = {
            "list_decks",
            "get_deck",
            "deck_as_dict",
            "upsert_deck",
            "add_card",
            "add_cards",
            "sync_anki",
            "show_help",
            "show_llmtxt",
            "show_examples",
        }
        assert expected.issubset(tool_names)


class TestSolveitDetection:
    """Tests for solveit context detection."""

    def test_check_solveit_returns_bool(self) -> None:
        from rememberit.tools import _check_solveit

        result = _check_solveit()
        assert isinstance(result, bool)

    def test_in_solveit_context_returns_bool(self) -> None:
        from rememberit.tools import _in_solveit_context

        result = _in_solveit_context()
        assert isinstance(result, bool)

    def test_is_solveit_returns_bool(self) -> None:
        from rememberit.tools import is_solveit

        result = is_solveit()
        assert isinstance(result, bool)

    def test_not_in_solveit_outside_dialog(self) -> None:
        from rememberit.tools import _in_solveit_context

        assert _in_solveit_context() is False


class TestToolsRegistered:
    """Tests for tools_registered function."""

    def test_tools_registered_returns_bool(self) -> None:
        from rememberit.tools import tools_registered

        result = tools_registered()
        assert isinstance(result, bool)


class TestLoadTools:
    """Tests for load_tools function."""

    def test_load_tools_returns_dict(self) -> None:
        from rememberit.tools import load_tools

        result = load_tools()
        assert isinstance(result, dict)
        assert "solveit" in result
        assert "registered" in result
        assert "tools" in result

    def test_load_tools_outside_solveit(self) -> None:
        from rememberit.tools import load_tools

        result = load_tools()
        assert result["solveit"] is False

    def test_load_tools_silent_flag(self) -> None:
        from rememberit.tools import load_tools

        result = load_tools(silent=True)
        assert isinstance(result, dict)


class TestIndividualTools:
    """Tests for individual tool functions (mocked)."""

    def test_list_decks_returns_string(self) -> None:
        from unittest.mock import MagicMock, patch

        from rememberit.tools import list_decks

        mock_collection = MagicMock()
        mock_collection.__iter__ = lambda self: iter([])
        mock_collection.__bool__ = lambda self: False

        with patch("rememberit.decks", return_value=mock_collection):
            result = list_decks()
            assert isinstance(result, str)
            assert "No decks found" in result

    def test_create_deck_returns_string(self) -> None:
        from unittest.mock import patch

        from rememberit.tools import create_deck

        with patch("rememberit.create_deck"):
            result = create_deck("Test Deck")
            assert isinstance(result, str)
            assert "Test Deck" in result

    def test_delete_deck_returns_string(self) -> None:
        from unittest.mock import patch

        from rememberit.tools import delete_deck

        with patch("rememberit.delete_deck"):
            result = delete_deck("Test Deck")
            assert isinstance(result, str)
            assert "Test Deck" in result

    def test_sync_anki_returns_string(self) -> None:
        from unittest.mock import MagicMock, patch

        from rememberit.tools import sync_anki

        mock_collection = MagicMock()
        mock_collection.__iter__ = lambda self: iter([])
        mock_collection.__len__ = lambda self: 0

        with patch("rememberit.sync", return_value=mock_collection):
            result = sync_anki()
            assert isinstance(result, str)
            assert "Synced" in result


class TestToolsInfo:
    """Tests for tools_info display function."""

    def test_tools_info_no_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        from rememberit.tools import tools_info

        tools_info()
        captured = capsys.readouterr()
        assert "RememberIt" in captured.out or len(captured.out) > 0


class TestHelpTools:
    """Tests for help/documentation tools."""

    def test_show_help_returns_string(self) -> None:
        from rememberit.tools import show_help

        result = show_help()
        assert isinstance(result, str)
        assert "API" in result
        assert "login" in result

    def test_show_llmtxt_returns_string(self) -> None:
        from rememberit.tools import show_llmtxt

        result = show_llmtxt()
        assert isinstance(result, str)
        assert "upsert_deck" in result

    def test_show_examples_returns_string(self) -> None:
        from rememberit.tools import show_examples

        result = show_examples()
        assert isinstance(result, str)
        assert "front" in result
        assert "back" in result


class TestDeckAsDict:
    """Tests for deck_as_dict tool."""

    def test_deck_as_dict_not_found(self) -> None:
        from unittest.mock import MagicMock, patch

        from rememberit.tools import deck_as_dict

        mock_collection = MagicMock()
        mock_collection.__getitem__ = MagicMock(side_effect=KeyError("not found"))

        with patch("rememberit.decks", return_value=mock_collection):
            result = deck_as_dict("NonexistentDeck")
            assert "not found" in result

    def test_deck_as_dict_returns_json(self) -> None:
        import json
        from unittest.mock import MagicMock, patch

        from rememberit.tools import deck_as_dict

        mock_deck = MagicMock()
        mock_deck.to_dict.return_value = {"name": "Test", "cards": []}
        mock_deck.sync.return_value = mock_deck

        mock_collection = MagicMock()
        mock_collection.__getitem__ = MagicMock(return_value=mock_deck)

        with patch("rememberit.decks", return_value=mock_collection):
            result = deck_as_dict("TestDeck")
            # Output includes hint text after JSON, so split on double newline
            json_part = result.split("\n\n")[0]
            parsed = json.loads(json_part)
            assert parsed["name"] == "Test"

    def test_deck_as_dict_by_index(self) -> None:
        import json
        from unittest.mock import MagicMock, patch

        from rememberit.tools import deck_as_dict

        mock_deck = MagicMock()
        mock_deck.to_dict.return_value = {"name": "First", "cards": []}
        mock_deck.sync.return_value = mock_deck

        mock_collection = MagicMock()
        mock_collection.__getitem__ = MagicMock(return_value=mock_deck)

        with patch("rememberit.decks", return_value=mock_collection):
            result = deck_as_dict("0")
            # Output includes hint text after JSON, so split on double newline
            json_part = result.split("\n\n")[0]
            parsed = json.loads(json_part)
            assert parsed["name"] == "First"
            mock_collection.__getitem__.assert_called_with(0)
