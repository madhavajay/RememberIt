from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, SupportsIndex, overload

from .formatting import decks_markdown_table, parse_card_field

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
    top_node: object | None
    current_deck_id: int | None
    collection_size_bytes: int | None
    media_size_bytes: int | None
    decks_flat: list[Mapping[str, Any]]
    _client: RememberItClient | None = None
    _raw_html: str | None = None

    def __iter__(self) -> Iterable[Mapping[str, Any]]:
        return iter(self.decks_flat)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.decks_flat)

    def __getitem__(self, key: int | str) -> Mapping[str, Any]:
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
            rows.append("<tr>" + "".join(f"<td>{row.get(h, '')}</td>" for h in headers) + "</tr>")
        header_html = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
        return f"<table><thead>{header_html}</thead><tbody>{''.join(rows)}</tbody></table>"


@dataclass
class CardSummary:
    id: str | None
    edit_url: str | None
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
    id: int | None
    front: str
    back: str
    raw_text: str
    edit_url: str | None
    deck: Deck | None = None
    _client: RememberItClient | None = None

    def update(self, *, front: str | None = None, back: str | None = None, tags: str = "") -> Card:
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


class CardCollection(list[Card]):
    @overload
    def __getitem__(self, key: SupportsIndex) -> Card: ...
    @overload
    def __getitem__(self, key: slice) -> list[Card]: ...
    @overload
    def __getitem__(self, key: str) -> Card: ...

    def __getitem__(self, key: SupportsIndex | str | slice) -> Card | list[Card]:
        if isinstance(key, slice):
            return super().__getitem__(key)
        if isinstance(key, str):
            key_lower = key.lower()
            for card in self:
                front = (card.front or "").lower()
                if (card.id is not None and str(card.id) == key) or key_lower in front:
                    return card
            raise KeyError(f"Card not found for key: {key}")
        return super().__getitem__(key)

    def _repr_html_(self) -> str:
        header_html = (
            "<tr><th style='padding:8px;border:1px solid #444;'>id</th>"
            "<th style='padding:8px;border:1px solid #444;'>front</th>"
            "<th style='padding:8px;border:1px solid #444;'>back</th></tr>"
        )
        rows = []
        for card in self:
            rows.append(
                f"<tr><td style='padding:8px;border:1px solid #444;vertical-align:top;'>"
                f"{card.id}</td>"
                f"<td style='padding:8px;border:1px solid #444;vertical-align:top;'>"
                f"{card.front}</td>"
                f"<td style='padding:8px;border:1px solid #444;vertical-align:top;'>"
                f"{card.back}</td></tr>"
            )
        return (
            "<table style='border-collapse:collapse;width:100%;'>"
            f"<thead style='background:#272822;color:#f8f8f2;'>{header_html}</thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )


@dataclass
class Deck:
    id: Any
    name: str
    path: str
    counts: Mapping[str, Any] = field(default_factory=dict)
    cards: CardCollection = field(default_factory=CardCollection)
    _client: RememberItClient | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any], client: RememberItClient | None = None) -> Deck:
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

    def sync(self) -> Deck:
        """Refresh this deck's cards from local collection (does not sync to AnkiWeb)."""
        if not self._client:
            raise RuntimeError("No client attached to deck")
        collection = self._client.refresh_local()
        for deck in collection:
            if deck.id == self.id or deck.name == self.name:
                self.cards = deck.cards
                for card in self.cards:
                    card.deck = self
                return self
        return self

    def add_card(self, front: str, back: str, tags: str = "") -> Deck:
        if not self._client:
            raise RuntimeError("No client attached to deck")
        self._client.add_card(deck_id=self.id, front=front, back=back, tags=tags)
        return self.sync()

    def delete(self) -> OperationResult:
        if not self._client:
            raise RuntimeError("No client attached to deck")
        result = self._client.remove_deck(self)
        return OperationResult(f"✓ {self.name} deleted", result.get("status_code", 200))

    def rename(self, new_name: str) -> OperationResult:
        if not self._client:
            raise RuntimeError("No client attached to deck")
        old_name = self.name
        result = self._client.rename_deck(self, new_name)
        code = result.get("status_code", 200)
        return OperationResult(f"✓ {old_name} renamed to {new_name}", code)

    def save_json(self, path: str) -> Path:
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

    def to_dict(self, *, raw: bool = False) -> dict[str, Any]:
        """
        Export deck cards as a dictionary for AI processing.

        Args:
            raw: If True, return raw HTML. If False (default), parse to plain text + metadata.

        Returns:
            Dict in upsert_deck format:
            {"name": str, "cards": [{front, back, front_type?, front_theme?, ...}, ...]}
        """
        cards_list: list[dict[str, Any]] = []
        for card in self.cards:
            if raw:
                cards_list.append({"front": card.front, "back": card.back})
            else:
                card_dict: dict[str, Any] = {}
                # Parse front
                front_parsed = parse_card_field(card.front)
                card_dict["front"] = front_parsed["content"]
                if front_parsed["type"] != "plain":
                    card_dict["front_type"] = front_parsed["type"]
                    if "lang" in front_parsed:
                        card_dict["front_lang"] = front_parsed["lang"]
                    if "theme" in front_parsed:
                        card_dict["front_theme"] = front_parsed["theme"]

                # Parse back
                back_parsed = parse_card_field(card.back)
                card_dict["back"] = back_parsed["content"]
                if back_parsed["type"] != "plain":
                    card_dict["back_type"] = back_parsed["type"]
                    if "lang" in back_parsed:
                        card_dict["back_lang"] = back_parsed["lang"]
                    if "theme" in back_parsed:
                        card_dict["back_theme"] = back_parsed["theme"]

                cards_list.append(card_dict)

        return {"name": self.name, "cards": cards_list}

    def json(self, indent: int = 2, *, raw: bool = False) -> str:
        """
        Export deck cards as a JSON string.
        Perfect for printing or passing to AI for editing.

        Args:
            indent: JSON indentation level (default: 2)
            raw: If True, return raw HTML. If False (default), parse to plain text + metadata.
        """
        return json.dumps(self.to_dict(raw=raw), ensure_ascii=False, indent=indent)

    def save_apkg(self, path: str, model_id: int = 1763445109221) -> Path:
        """
        Write an .apkg using genanki if available. Basic model only; no media.
        """
        try:
            import genanki  # type: ignore[import-not-found]
        except ImportError as err:
            msg = "genanki is not installed; run `pip install genanki` to enable save_apkg"
            raise RuntimeError(msg) from err

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
                    "afmt": '{{FrontSide}}<hr id="answer">{{Answer}}',
                }
            ],
        )
        for card in self.cards:
            gdeck.add_note(genanki.Note(model=model, fields=[card.front, card.back]))
        pkg = genanki.Package(gdeck)
        pkg.write_to_file(path)
        return Path(path)

    def __getitem__(self, key: int | str) -> Card:
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
            "<br/>" + self.cards._repr_html_()
        )

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"Deck(id={self.id}, path={self.path!r}, cards={len(self.cards)})"


class DeckCollection(list[Deck]):
    def __init__(self, decks: Iterable[Deck], client: RememberItClient | None = None) -> None:
        super().__init__(decks)
        self._client = client

    def delete(self, deck: Deck | str | int) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("No client attached to DeckCollection")
        return self._client.remove_deck(deck)

    def rename(self, deck: Deck | str | int, new_name: str) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("No client attached to DeckCollection")
        return self._client.rename_deck(deck, new_name)

    @overload
    def __getitem__(self, key: SupportsIndex) -> Deck: ...
    @overload
    def __getitem__(self, key: slice) -> list[Deck]: ...
    @overload
    def __getitem__(self, key: str) -> Deck: ...

    def __getitem__(self, key: SupportsIndex | str | slice) -> Deck | list[Deck]:
        if isinstance(key, slice):
            return super().__getitem__(key)
        if isinstance(key, str):
            for deck in self:
                if str(deck.id) == str(key) or deck.name == key or deck.path == key:
                    return deck
            # Auto-create deck if not found (by string name)
            if self._client:
                new_deck = self._client.create_deck(key)
                self.append(new_deck)
                return new_deck
            raise KeyError(f"Deck not found for key: {key}")
        return super().__getitem__(key)

    def get(self, key: str, default: Deck | None = None) -> Deck | None:
        """Get deck by name/id, returning default if not found."""
        try:
            return self[key]
        except KeyError:
            return default

    def get_or_create(self, name: str) -> Deck:
        """Get deck by name, creating it if it doesn't exist."""
        try:
            return self[name]
        except KeyError:
            if not self._client:
                raise RuntimeError("No client attached to DeckCollection")
            deck = self._client.create_deck(name)
            self.append(deck)
            return deck

    def _repr_html_(self) -> str:
        header = "<tr><th>id</th><th>path</th><th>cards</th></tr>"
        rows = "".join(
            f"<tr><td>{d.id}</td><td>{d.path}</td><td>{len(d.cards)}</td></tr>" for d in self
        )
        return f"<table><thead>{header}</thead><tbody>{rows}</tbody></table>"
