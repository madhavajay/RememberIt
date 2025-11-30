"""Tests for rememberit.models module."""

from __future__ import annotations

import json

import pytest


class TestCard:
    """Tests for Card class."""

    def test_card_creation(self) -> None:
        from rememberit.models import Card

        card = Card(id=1, front="Question", back="Answer", raw_text="Q\x1fA", edit_url=None)
        assert card.id == 1
        assert card.front == "Question"
        assert card.back == "Answer"

    def test_card_optional_fields(self) -> None:
        from rememberit.models import Card

        card = Card(id=1, front="Q", back="A", raw_text="raw", edit_url="http://test.com")
        assert card.raw_text == "raw"
        assert card.edit_url == "http://test.com"

    def test_card_repr(self) -> None:
        from rememberit.models import Card

        card = Card(id=1, front="Question", back="Answer", raw_text="", edit_url=None)
        r = repr(card)
        assert "Question" in r
        assert "Answer" in r


class TestCardCollection:
    """Tests for CardCollection class."""

    def test_empty_collection(self) -> None:
        from rememberit.models import CardCollection

        coll = CardCollection([])
        assert len(coll) == 0

    def test_collection_iteration(self) -> None:
        from rememberit.models import Card, CardCollection

        cards = [
            Card(id=1, front="Q1", back="A1", raw_text="", edit_url=None),
            Card(id=2, front="Q2", back="A2", raw_text="", edit_url=None),
        ]
        coll = CardCollection(cards)

        assert len(coll) == 2
        assert list(coll) == cards

    def test_collection_indexing_by_front(self) -> None:
        from rememberit.models import Card, CardCollection

        cards = [Card(id=1, front="Question", back="Answer", raw_text="", edit_url=None)]
        coll = CardCollection(cards)

        found = coll["Question"]
        assert found.back == "Answer"

    def test_collection_indexing_not_found(self) -> None:
        from rememberit.models import Card, CardCollection

        cards = [Card(id=1, front="Question", back="Answer", raw_text="", edit_url=None)]
        coll = CardCollection(cards)

        with pytest.raises(KeyError):
            _ = coll["Nonexistent"]

    def test_collection_indexing_by_int(self) -> None:
        from rememberit.models import Card, CardCollection

        cards = [
            Card(id=1, front="Q1", back="A1", raw_text="", edit_url=None),
            Card(id=2, front="Q2", back="A2", raw_text="", edit_url=None),
        ]
        coll = CardCollection(cards)

        assert coll[0].front == "Q1"
        assert coll[1].front == "Q2"


class TestDeck:
    """Tests for Deck class."""

    def test_deck_from_row(self) -> None:
        from rememberit.models import Deck

        row = {
            "id": 123,
            "name": "Test Deck",
            "path": "Test::Deck",
            "total": 5,
            "new": "2",
            "learn": "1",
            "review": "2",
            "total_incl_children": 5,
        }
        deck = Deck.from_row(row)

        assert deck.id == 123
        assert deck.name == "Test Deck"
        assert deck.path == "Test::Deck"

    def test_deck_to_dict(self) -> None:
        from rememberit.models import Card, CardCollection, Deck

        row = {"id": 1, "name": "Test", "path": "Test", "total": 1}
        deck = Deck.from_row(row)
        deck.cards = CardCollection([Card(id=1, front="Q", back="A", raw_text="", edit_url=None)])

        d = deck.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "Test"
        assert "cards" in d

    def test_deck_json(self) -> None:
        from rememberit.models import Card, CardCollection, Deck

        row = {"id": 1, "name": "Test", "path": "Test", "total": 1}
        deck = Deck.from_row(row)
        deck.cards = CardCollection([Card(id=1, front="Q", back="A", raw_text="", edit_url=None)])

        j = deck.json()
        assert isinstance(j, str)
        parsed = json.loads(j)
        assert parsed["name"] == "Test"

    def test_deck_repr(self) -> None:
        from rememberit.models import Deck

        row = {"id": 1, "name": "Test", "path": "Test", "total": 0}
        deck = Deck.from_row(row)
        r = repr(deck)
        assert "Test" in r


class TestDeckCollection:
    """Tests for DeckCollection class."""

    def test_empty_collection(self) -> None:
        from rememberit.models import DeckCollection

        coll = DeckCollection([])
        assert len(coll) == 0

    def test_collection_iteration(self) -> None:
        from rememberit.models import Deck, DeckCollection

        decks = [
            Deck.from_row({"id": 1, "name": "Deck1", "path": "Deck1", "total": 0}),
            Deck.from_row({"id": 2, "name": "Deck2", "path": "Deck2", "total": 0}),
        ]
        coll = DeckCollection(decks)

        assert len(coll) == 2

    def test_collection_indexing_by_name(self) -> None:
        from rememberit.models import Deck, DeckCollection

        decks = [Deck.from_row({"id": 1, "name": "MyDeck", "path": "MyDeck", "total": 0})]
        coll = DeckCollection(decks)

        found = coll["MyDeck"]
        assert found.id == 1

    def test_collection_indexing_by_int_index(self) -> None:
        from rememberit.models import Deck, DeckCollection

        decks = [
            Deck.from_row({"id": 123, "name": "Test", "path": "Test", "total": 0}),
            Deck.from_row({"id": 456, "name": "Test2", "path": "Test2", "total": 0}),
        ]
        coll = DeckCollection(decks)

        assert coll[0].name == "Test"
        assert coll[1].name == "Test2"

    def test_collection_get_method(self) -> None:
        from rememberit.models import Deck, DeckCollection

        decks = [Deck.from_row({"id": 1, "name": "Test", "path": "Test", "total": 0})]
        coll = DeckCollection(decks)

        assert coll.get("Test") is not None
        assert coll.get("Nonexistent") is None


class TestOperationResult:
    """Tests for OperationResult class."""

    def test_operation_result(self) -> None:
        from rememberit.models import OperationResult

        result = OperationResult("Success", 200)
        assert result.message == "Success"
        assert result.status_code == 200

    def test_repr(self) -> None:
        from rememberit.models import OperationResult

        result = OperationResult("Done", 201)
        r = repr(result)
        assert "Done" in r


class TestCardSummary:
    """Tests for CardSummary class."""

    def test_card_summary(self) -> None:
        from rememberit.models import CardSummary

        summary = CardSummary(id="123", edit_url="http://test.com", text="Card text")
        assert summary.id == "123"
        assert summary.text == "Card text"


class TestDeckListResult:
    """Tests for DeckListResult class."""

    def test_deck_list_result(self) -> None:
        from rememberit.models import DeckListResult

        result = DeckListResult(
            top_node=None,
            current_deck_id=1,
            collection_size_bytes=1000,
            media_size_bytes=500,
            decks_flat=[{"id": 1, "name": "Test", "path": "Test"}],
        )
        assert result.current_deck_id == 1
        assert len(result) == 1

    def test_deck_list_iteration(self) -> None:
        from rememberit.models import DeckListResult

        decks = [
            {"id": 1, "name": "Deck1"},
            {"id": 2, "name": "Deck2"},
        ]
        result = DeckListResult(
            top_node=None,
            current_deck_id=None,
            collection_size_bytes=None,
            media_size_bytes=None,
            decks_flat=decks,
        )
        assert len(list(result)) == 2


class TestCardUpdateWithImages:
    """Tests for Card.update() with image auto-conversion."""

    def test_update_with_image_path(self) -> None:
        from pathlib import Path
        from unittest.mock import MagicMock

        from rememberit.models import Card

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        # Mock client
        mock_client = MagicMock()
        mock_client.update_card = MagicMock(return_value={"status_code": 200})

        card = Card(
            id=1,
            front="Question",
            back="Old answer",
            raw_text="",
            edit_url=None,
            _client=mock_client,
        )

        # Update with image path
        card.update(back=pickles_path)

        # Verify update_card was called with formatted image HTML
        assert mock_client.update_card.called
        call_args = mock_client.update_card.call_args
        back_value = call_args.kwargs["back"]
        assert isinstance(back_value, str)
        assert "<img" in back_value
        assert "base64" in back_value

    def test_update_with_pil_image(self) -> None:
        from pathlib import Path
        from unittest.mock import MagicMock

        from rememberit.models import Card

        try:
            from PIL import Image
        except ImportError:
            return

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        pil_image = Image.open(pickles_path)

        mock_client = MagicMock()
        mock_client.update_card = MagicMock(return_value={"status_code": 200})

        card = Card(id=1, front="Q", back="A", raw_text="", edit_url=None, _client=mock_client)

        card.update(back=pil_image)

        assert mock_client.update_card.called
        call_args = mock_client.update_card.call_args
        back_value = call_args.kwargs["back"]
        assert isinstance(back_value, str)
        assert "<img" in back_value
        assert "base64" in back_value

    def test_update_with_string_preserves_text(self) -> None:
        from unittest.mock import MagicMock

        from rememberit.models import Card

        mock_client = MagicMock()
        mock_client.update_card = MagicMock(return_value={"status_code": 200})

        card = Card(id=1, front="Q", back="A", raw_text="", edit_url=None, _client=mock_client)

        card.update(back="New answer text")

        assert mock_client.update_card.called
        call_args = mock_client.update_card.call_args
        back_value = call_args.kwargs["back"]
        assert back_value == "New answer text"

    def test_update_with_mock_image_object(self) -> None:
        from unittest.mock import MagicMock

        from rememberit.models import Card

        class MockImageObject:
            def _repr_png_(self) -> bytes:
                return (
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
                    b"\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc"
                    b"\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                )

        mock_client = MagicMock()
        mock_client.update_card = MagicMock(return_value={"status_code": 200})

        card = Card(id=1, front="Q", back="A", raw_text="", edit_url=None, _client=mock_client)

        mock_img = MockImageObject()
        card.update(back=mock_img)

        assert mock_client.update_card.called
        call_args = mock_client.update_card.call_args
        back_value = call_args.kwargs["back"]
        assert isinstance(back_value, str)
        assert "<img" in back_value


class TestDeckAddCardWithImages:
    """Tests for Deck.add_card() with image auto-conversion."""

    def test_add_card_with_image_path(self) -> None:
        from pathlib import Path
        from unittest.mock import MagicMock

        from rememberit.models import Deck

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        mock_client = MagicMock()
        mock_client.add_card = MagicMock(return_value={"status_code": 200})

        deck = Deck(id=1, name="Test", path="Test", _client=mock_client)

        # Mock sync to avoid needing full client setup
        deck.sync = MagicMock(return_value=deck)

        deck.add_card(front="Question", back=pickles_path)

        assert mock_client.add_card.called
        call_args = mock_client.add_card.call_args
        back_value = call_args.kwargs["back"]
        assert isinstance(back_value, str)
        assert "<img" in back_value
        assert "base64" in back_value

    def test_add_card_with_pil_image(self) -> None:
        from pathlib import Path
        from unittest.mock import MagicMock

        from rememberit.models import Deck

        try:
            from PIL import Image
        except ImportError:
            return

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        pil_image = Image.open(pickles_path)

        mock_client = MagicMock()
        mock_client.add_card = MagicMock(return_value={"status_code": 200})

        deck = Deck(id=1, name="Test", path="Test", _client=mock_client)
        deck.sync = MagicMock(return_value=deck)

        deck.add_card(front="Question", back=pil_image)

        assert mock_client.add_card.called
        call_args = mock_client.add_card.call_args
        back_value = call_args.kwargs["back"]
        assert isinstance(back_value, str)
        assert "<img" in back_value

    def test_add_card_with_both_images(self) -> None:
        from pathlib import Path
        from unittest.mock import MagicMock

        from rememberit.models import Deck

        pickles_path = Path(__file__).parent.parent / "src/rememberit/image/pickles.jpg"
        if not pickles_path.exists():
            return

        mock_client = MagicMock()
        mock_client.add_card = MagicMock(return_value={"status_code": 200})

        deck = Deck(id=1, name="Test", path="Test", _client=mock_client)
        deck.sync = MagicMock(return_value=deck)

        deck.add_card(front=pickles_path, back=pickles_path)

        assert mock_client.add_card.called
        call_args = mock_client.add_card.call_args
        front_value = call_args.kwargs["front"]
        back_value = call_args.kwargs["back"]
        assert isinstance(front_value, str)
        assert isinstance(back_value, str)
        assert "<img" in front_value
        assert "<img" in back_value
