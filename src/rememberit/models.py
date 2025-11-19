from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping, Optional, Union, TYPE_CHECKING
from pathlib import Path
import json

from .formatting import decks_markdown_table
from .proto import DeckNode

if TYPE_CHECKING:  # pragma: no cover
    from .client import RememberItClient


@dataclass
class OperationResult:
    """Result of a deck/card operation with user-friendly display."""
    message: str
    status_code: int = 200

    def __repr__(self) -> str:
        return self.message

    def _repr_html_(self) -> str:
        return f"<div>{self.message}</div>"


@dataclass
class DeckListResult:
    top_node: Optional[DeckNode]
    current_deck_id: Optional[int]
    collection_size_bytes: Optional[int]
    media_size_bytes: Optional[int]
    decks_flat: List[Mapping[str, Any]]
    _client: Optional["RememberItClient"] = None
    _raw_html: Optional[str] = None

    def __iter__(self) -> Iterable[Mapping[str, Any]]:
        return iter(self.decks_flat)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.decks_flat)

    def __getitem__(self, key: Union[int, str]) -> Mapping[str, Any]:
        if isinstance(key, int):
            return self.decks_flat[key]
        for row in self.decks_flat:
            if str(row.get("id")) == str(key) or row.get("name") == key or row.get("path") == key:
                return row
        raise KeyError(f"Deck not found for key: {key}")

    def markdown(self) -> str:
        return decks_markdown_table(self.decks_flat)

    def _repr_html_(self) -> str:
        # Render an HTML table for Jupyter
        headers = ["id", "path", "new", "learn", "review", "total", "total_incl_children"]
        rows = []
        for row in self.decks_flat:
            rows.append("<tr>" + "".join(f"<td>{row.get(h,'')}</td>" for h in headers) + "</tr>")
        header_html = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
        return f"<table><thead>{header_html}</thead><tbody>{''.join(rows)}</tbody></table>"


@dataclass
class CardSummary:
    id: Optional[str]
    edit_url: Optional[str]
    text: str

    def _repr_html_(self) -> str:
        return (
            "<table>"
            "<thead><tr><th>field</th><th>value</th></tr></thead>"
            "<tbody>"
            f"<tr><td>id</td><td>{self.id}</td></tr>"
            f"<tr><td>edit</td><td>{self.edit_url}</td></tr>"
            f"<tr><td>text</td><td>{self.text}</td></tr>"
            "</tbody></table>"
        )


@dataclass
class Card:
    id: Optional[int]
    front: str
    back: str
    raw_text: str
    edit_url: Optional[str]
    deck: Optional["Deck"] = None
    _client: Optional["RememberItClient"] = None

    def update(self, *, front: Optional[str] = None, back: Optional[str] = None, tags: str = ""):
        if not self._client or self.id is None:
            raise RuntimeError("Cannot update card without client and id")
        new_front = front if front is not None else self.front
        new_back = back if back is not None else self.back
        self._client.update_card(note_id=self.id, front=new_front, back=new_back, tags=tags)
        self.front, self.back = new_front, new_back
        return self

    def _repr_html_(self) -> str:
        return (
            "<table>"
            "<thead><tr><th>field</th><th>value</th></tr></thead>"
            "<tbody>"
            f"<tr><td>id</td><td>{self.id}</td></tr>"
            f"<tr><td>front</td><td>{self.front}</td></tr>"
            f"<tr><td>back</td><td>{self.back}</td></tr>"
            f"<tr><td>deck</td><td>{self.deck.path if self.deck else ''}</td></tr>"
            "</tbody></table>"
        )

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"Card(id={self.id}, front={self.front!r}, back={self.back!r})"


class CardCollection(list):
    def __getitem__(self, key: Union[int, str]) -> Card:
        if isinstance(key, int):
            return super().__getitem__(key)
        key_lower = key.lower()
        for card in self:
            front = (card.front or "").lower()
            if (card.id is not None and str(card.id) == key) or key_lower in front:
                return card
        raise KeyError(f"Card not found for key: {key}")

    def _repr_html_(self) -> str:
        header_html = "<tr><th>id</th><th>front</th><th>back</th></tr>"
        rows = []
        for card in self:
            rows.append(
                f"<tr><td>{card.id}</td><td>{card.front}</td><td>{card.back}</td></tr>"
            )
        return f"<table><thead>{header_html}</thead><tbody>{''.join(rows)}</tbody></table>"


@dataclass
class Deck:
    id: Any
    name: str
    path: str
    counts: Mapping[str, Any] = field(default_factory=dict)
    cards: CardCollection = field(default_factory=CardCollection)
    _client: Optional["RememberItClient"] = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any], client: Optional["RememberItClient"] = None) -> "Deck":
        return cls(
            id=row.get("id"),
            name=str(row.get("name") or ""),
            path=str(row.get("path") or ""),
            counts=row,
            cards=CardCollection(),
            _client=client,
        )

    def update_from_row(self, row: Mapping[str, Any]) -> None:
        self.counts = row
        self.id = row.get("id", self.id)
        self.name = str(row.get("name") or self.name)
        self.path = str(row.get("path") or self.path)

    def sync(self):
        """Refresh this deck's cards by re-syncing the entire collection."""
        if not self._client:
            raise RuntimeError("No client attached to deck")
        # Re-sync entire collection to get fresh data
        collection = self._client.sync()
        # Find this deck in the refreshed collection
        for deck in collection:
            if deck.id == self.id or deck.name == self.name:
                # Update this deck's cards with the refreshed data
                self.cards = deck.cards
                for card in self.cards:
                    card.deck = self
                return self
        # If deck not found, return with empty cards
        self.cards = CardCollection([])
        return self

    def add_card(self, front: str, back: str, tags: str = "", model_id: Optional[int] = None):
        if not self._client:
            raise RuntimeError("No client attached to deck")
        self._client.add_card(deck_id=self.id, front=front, back=back, tags=tags, model_id=model_id)
        return self.sync()

    def delete(self):
        if not self._client:
            raise RuntimeError("No client attached to deck")
        result = self._client.remove_deck(self)
        return OperationResult(f"✓ {self.name} deleted", result.get("status_code", 200))

    def rename(self, new_name: str):
        if not self._client:
            raise RuntimeError("No client attached to deck")
        old_name = self.name
        result = self._client.rename_deck(self, new_name)
        return OperationResult(f"✓ {old_name} renamed to {new_name}", result.get("status_code", 200))

    def save_json(self, path: str):
        """
        Export this deck's cards to a JSON file for AI-friendly editing.
        Schema: {name, deck_id, cards:[{note_id?, front, back, tags?}]}
        """
        file_path = Path(path)
        payload = {
            "name": self.name,
            "deck_id": self.id,
            "cards": [
                {
                    "note_id": card.id,
                    "front": card.front,
                    "back": card.back,
                    "tags": "",
                }
                for card in self.cards
            ],
        }
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def to_dict(self):
        """
        Export deck cards as a dictionary for AI processing.
        Returns: {"name": str, "cards": [{"front": str, "back": str}, ...]}
        """
        return {
            "name": self.name,
            "cards": [
                {
                    "front": card.front,
                    "back": card.back,
                }
                for card in self.cards
            ],
        }

    def json(self, indent: int = 2):
        """
        Export deck cards as a JSON string.
        Perfect for printing or passing to AI for editing.
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_apkg(self, path: str, model_id: int = 1763445109221):
        """
        Write an .apkg using genanki if available. Basic model only; no media.
        """
        try:
            import genanki  # type: ignore
        except ImportError as err:
            raise RuntimeError("genanki is not installed; run `pip install genanki` to enable save_apkg") from err

        deck_id = int(self.id) if self.id is not None else 0
        gdeck = genanki.Deck(deck_id, self.name or "")
        model = genanki.Model(
            model_id,
            "Basic Model",
            fields=[{"name": "Question"}, {"name": "Answer"}],
            templates=[
                {
                    "name": "Card 1",
                    "qfmt": "{{Question}}",
                    "afmt": "{{FrontSide}}<hr id=\"answer\">{{Answer}}",
                }
            ],
        )
        for card in self.cards:
            gdeck.add_note(genanki.Note(model=model, fields=[card.front, card.back]))
        pkg = genanki.Package(gdeck)
        pkg.write_to_file(path)
        return Path(path)

    def __getitem__(self, key: Union[int, str]) -> Card:
        return self.cards[key]

    def _repr_html_(self) -> str:
        counts = {
            "new": self.counts.get("new"),
            "learn": self.counts.get("learn"),
            "review": self.counts.get("review"),
            "total": self.counts.get("total"),
        }
        info = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in counts.items())
        return (
            "<table>"
            "<thead><tr><th colspan='2'>Deck</th></tr></thead>"
            f"<tbody><tr><td>id</td><td>{self.id}</td></tr>"
            f"<tr><td>path</td><td>{self.path}</td></tr>"
            f"{info}</tbody></table>"
            "<br/>"
            + self.cards._repr_html_()
        )

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"Deck(id={self.id}, path={self.path!r}, cards={len(self.cards)})"


class DeckCollection(list):
    def __init__(self, decks: Iterable[Deck], client: Optional["RememberItClient"] = None):
        super().__init__(decks)
        self._client = client

    def delete(self, deck: Deck | str | int):
        if not self._client:
            raise RuntimeError("No client attached to DeckCollection")
        return self._client.remove_deck(deck)

    def rename(self, deck: Deck | str | int, new_name: str):
        if not self._client:
            raise RuntimeError("No client attached to DeckCollection")
        return self._client.rename_deck(deck, new_name)

    def __getitem__(self, key: Union[int, str]) -> Deck:
        if isinstance(key, int):
            return super().__getitem__(key)
        for deck in self:
            if str(deck.id) == str(key) or deck.name == key or deck.path == key:
                return deck
        raise KeyError(f"Deck not found for key: {key}")

    def _repr_html_(self) -> str:
        header = "<tr><th>id</th><th>path</th><th>cards</th></tr>"
        rows = "".join(
            f"<tr><td>{d.id}</td><td>{d.path}</td><td>{len(d.cards)}</td></tr>" for d in self
        )
        return f"<table><thead>{header}</thead><tbody>{rows}</tbody></table>"
