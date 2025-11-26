from __future__ import annotations

import contextlib
import io
import json
import os
import random
import string
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

import requests
import zstandard as zstd
from anki.collection import Collection
from anki.models import ModelManager
from anki.notes import Note
from anki.sync_pb2 import SyncAuth as ProtoSyncAuth

from .config import DEFAULT_CONFIG_DIRNAME
from .models import Card, CardCollection, Deck, DeckCollection

# Files on disk
STORE_DIR = Path.home() / DEFAULT_CONFIG_DIRNAME
COLLECTION_PATH = STORE_DIR / "collection.anki2"
SESSION_PATH = STORE_DIR / "config.json"

DEFAULT_ENDPOINT = "https://sync.ankiweb.net/"
SYNC_VERSION = 10
CLIENT_VERSION = "rememberit,0.1"


def _generate_session_key() -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(8))


def _close_collection_quiet(col: Collection) -> None:
    """Close collection while suppressing Anki's debug output."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        col.close()


def _download_collection(hkey: str, endpoint: str) -> bytes:
    """Download collection directly from AnkiWeb sync endpoint."""
    url = endpoint.rstrip("/") + "/sync/download"
    session_key = _generate_session_key()
    header = json.dumps({"v": SYNC_VERSION, "k": hkey, "c": CLIENT_VERSION, "s": session_key})
    body = b"{}"
    cctx = zstd.ZstdCompressor()
    compressed: bytes = cctx.compress(body)
    resp = requests.post(
        url,
        data=compressed,
        headers={"anki-sync": header, "Content-Type": "application/octet-stream"},
        timeout=120,
        allow_redirects=False,
    )
    if resp.status_code in (307, 308):
        redirect_url = resp.headers.get("Location", endpoint)
        return _download_collection(hkey, redirect_url)
    resp.raise_for_status()
    data: bytes = resp.content
    if data[:4] == b"\x28\xb5\x2f\xfd":
        dctx = zstd.ZstdDecompressor()
        data = dctx.decompress(data)
    return data


class RememberItError(Exception):
    """Custom error class for RememberIt operations."""


@dataclass
class Session:
    """Serialized session credentials for Anki sync."""

    hkey: str
    endpoint: str
    username: str | None = None
    password: str | None = None


def load_session() -> Session | None:
    """Load session from ~/.rememberit/config.json if present."""
    if not SESSION_PATH.exists():
        return None
    raw = json.loads(SESSION_PATH.read_text())
    return Session(
        hkey=raw["hkey"],
        endpoint=raw.get("endpoint") or DEFAULT_ENDPOINT,
        username=raw.get("username"),
        password=raw.get("password"),
    )


def save_session(sess: Session) -> Session:
    """Persist session to ~/.rememberit/config.json."""
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(json.dumps(sess.__dict__, indent=2))
    try:
        SESSION_PATH.chmod(0o600)
    except PermissionError:
        pass
    return sess


_T = TypeVar("_T")


def _run_in_thread(fn: Callable[[], _T]) -> _T:
    """Run blocking Anki backend calls off the main thread."""
    result: dict[str, _T] = {}
    error: dict[str, Exception] = {}

    def wrapper() -> None:
        try:
            result["value"] = fn()
        except Exception as exc:  # noqa: BLE001
            error["exc"] = exc

    t = threading.Thread(target=wrapper)
    t.start()
    t.join()
    if "exc" in error:
        raise error["exc"]
    return result["value"]


class RememberItClient:
    """Thin wrapper around the official `anki` package."""

    def __init__(self, session: Session | None = None) -> None:
        self.session = session or load_session()
        self._deck_cache: dict[str, Deck] = {}
        self._deck_order: list[str] = []

    # --- Session / sync -------------------------------------------------
    def login(
        self, user: str | None = None, pw: str | None = None, *, endpoint: str | None = None
    ) -> Session:
        """Authenticate and store session (hkey + endpoint)."""
        user = user or os.getenv("ANKI_USER")
        pw = pw or os.getenv("ANKI_PASS")
        if not user or not pw:
            raise RememberItError("Provide credentials or set ANKI_USER / ANKI_PASS")

        STORE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STORE_DIR / "_login.anki2"

        # Suppress Anki's debug output during collection operations
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            col = Collection(str(tmp))

            def _do_login() -> Any:
                return col.sync_login(username=user, password=pw, endpoint=endpoint)

            auth = _run_in_thread(_do_login)
            col.close()

        tmp.unlink(missing_ok=True)
        self.session = save_session(
            Session(
                hkey=auth.hkey,
                endpoint=auth.endpoint or DEFAULT_ENDPOINT,
                username=user,
                password=pw,
            )
        )
        return self.session

    def get_sync_key(self) -> str | None:
        return self.session.hkey if self.session else None

    def logout(self) -> None:
        """Clear cached session; collection file remains on disk."""
        self.session = None
        if SESSION_PATH.exists():
            SESSION_PATH.unlink()

    def _ensure_collection(self) -> Collection:
        """Open local collection; download from AnkiWeb if missing."""
        if not self.session:
            raise RememberItError("Not logged in. Call login() first.")

        STORE_DIR.mkdir(parents=True, exist_ok=True)
        exists = COLLECTION_PATH.exists()
        if not exists:
            data = _download_collection(self.session.hkey, self.session.endpoint)
            COLLECTION_PATH.write_bytes(data)
        # Suppress Anki's debug output
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return Collection(str(COLLECTION_PATH))

    def sync_down(self) -> None:
        """Pull latest collection from AnkiWeb."""
        if not self.session:
            raise RememberItError("Not logged in. Call login() first.")
        session = self.session

        def _run() -> None:
            col = self._ensure_collection()
            # Suppress Anki's debug output
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                col.sync_collection(
                    auth=ProtoSyncAuth(hkey=session.hkey, endpoint=session.endpoint),
                    sync_media=False,
                )
                col.close()

        _run_in_thread(_run)
        self._deck_cache.clear()
        self._deck_order = []

    def sync_up(self) -> None:
        """Push local changes to AnkiWeb."""
        if not self.session:
            raise RememberItError("Not logged in. Call login() first.")
        if not COLLECTION_PATH.exists():
            raise RememberItError("No local collection; run sync_down first.")
        session = self.session

        def _run() -> None:
            # Suppress Anki's debug output
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                col = Collection(str(COLLECTION_PATH))
                col.sync_collection(
                    auth=ProtoSyncAuth(hkey=session.hkey, endpoint=session.endpoint),
                    sync_media=False,
                )
                col.close()

        _run_in_thread(_run)
        self._deck_cache.clear()
        self._deck_order = []

    # --- Deck/card helpers ----------------------------------------------
    def decks(self) -> DeckCollection:
        """Return cached decks, syncing down if cache is empty."""
        if not self._deck_cache:
            self.sync_down()
            self._refresh_cache_from_collection()
        ordered = [self._deck_cache[k] for k in self._deck_order if k in self._deck_cache]
        return DeckCollection(ordered, client=self)

    def sync(self) -> DeckCollection:
        """Force a fresh sync and return decks."""
        self.sync_down()
        self._refresh_cache_from_collection()
        ordered = [self._deck_cache[k] for k in self._deck_order if k in self._deck_cache]
        return DeckCollection(ordered, client=self)

    def add_card(self, deck_id: int, front: str, back: str, tags: str = "") -> dict[str, Any]:
        col = self._ensure_collection()
        mm: ModelManager = col.models
        model = mm.by_name("Basic")
        if not model:
            _close_collection_quiet(col)
            raise RememberItError("Basic note type not found in collection")
        note = Note(col, model)
        note.fields[0] = front
        note.fields[1] = back
        if tags:
            note.tags = tags.split()
        col.add_note(note, deck_id=deck_id)  # type: ignore[arg-type]
        _close_collection_quiet(col)
        self._deck_cache.clear()
        self._deck_order = []
        return {"status_code": 200}

    def update_card(
        self,
        note_id: int,
        front: str,
        back: str,
        tags: str = "",
        deck_id: int | None = None,
    ) -> dict[str, Any]:
        col = self._ensure_collection()
        note = col.get_note(note_id)  # type: ignore[arg-type]
        if not note:
            _close_collection_quiet(col)
            raise RememberItError(f"Note not found: {note_id}")
        note.fields[0] = front
        note.fields[1] = back
        if tags:
            note.tags = tags.split()
        col.update_note(note)
        _close_collection_quiet(col)
        self._deck_cache.clear()
        self._deck_order = []
        return {"status_code": 200}

    def create_deck(self, name: str) -> Deck:
        col = self._ensure_collection()
        deck_id = col.decks.id(name, create=True)
        _close_collection_quiet(col)
        deck_row = {
            "id": deck_id,
            "name": name,
            "path": name,
            "total": 0,
            "new": "",
            "learn": "",
            "review": "",
            "total_incl_children": 0,
        }
        deck_obj = Deck.from_row(deck_row, client=self)
        deck_obj.cards = CardCollection([])
        key = str(name)
        self._deck_cache[key] = deck_obj
        self._deck_order.append(key)
        return deck_obj

    def remove_deck(self, deck: Deck | str | int) -> dict[str, Any]:
        decks = self.decks()
        if isinstance(deck, Deck):
            deck_obj = deck
        else:
            deck_obj = decks[deck]
        col = self._ensure_collection()
        col.decks.remove([deck_obj.id])
        _close_collection_quiet(col)
        self._deck_cache.pop(self._deck_key_from_deck(deck_obj), None)
        self._deck_order = [k for k in self._deck_order if k != self._deck_key_from_deck(deck_obj)]
        return {"status_code": 200}

    def rename_deck(self, deck: Deck | str | int, new_name: str) -> dict[str, Any]:
        decks = self.decks()
        if isinstance(deck, Deck):
            deck_obj = deck
        else:
            deck_obj = decks[deck]
        col = self._ensure_collection()
        col.decks.rename(deck_obj.id, new_name)
        _close_collection_quiet(col)
        # Update cache
        old_key = self._deck_key_from_deck(deck_obj)
        deck_obj.name = new_name
        deck_obj.path = new_name
        new_key = self._deck_key_from_deck(deck_obj)
        self._deck_cache.pop(old_key, None)
        self._deck_cache[new_key] = deck_obj
        self._deck_order = [new_key if k == old_key else k for k in self._deck_order]
        return {"status_code": 200}

    # --- Internal helpers -----------------------------------------------
    def _refresh_cache_from_collection(self) -> None:
        col = self._ensure_collection()
        decks: list[Deck] = []
        for deck_info in col.decks.all_names_and_ids():
            deck_id = deck_info.id
            name = deck_info.name
            cards: list[Card] = []
            for cid in col.find_cards(f'deck:"{name}"'):
                card_obj = col.get_card(cid)
                note = card_obj.note()
                front = note.fields[0] if len(note.fields) > 0 else ""
                back = note.fields[1] if len(note.fields) > 1 else ""
                cards.append(
                    Card(
                        id=note.id,
                        front=front,
                        back=back,
                        raw_text="\x1f".join(note.fields),
                        edit_url=None,
                        deck=None,
                        _client=self,
                    )
                )
            deck_row = {
                "id": deck_id,
                "name": name,
                "path": name,
                "total": len(cards),
                "new": "",
                "learn": "",
                "review": "",
                "total_incl_children": len(cards),
            }
            deck_obj = Deck.from_row(deck_row, client=self)
            deck_obj.cards = CardCollection(cards)
            for card in deck_obj.cards:
                card.deck = deck_obj
            decks.append(deck_obj)
        _close_collection_quiet(col)
        self._deck_cache = {self._deck_key_from_deck(d): d for d in decks}
        self._deck_order = [self._deck_key_from_deck(d) for d in decks]

    def _deck_key_from_deck(self, deck: Deck) -> str:
        return str(deck.path or deck.name or deck.id or "")

    def refresh_local(self) -> DeckCollection:
        """Refresh cache from local collection without syncing to AnkiWeb."""
        self._refresh_cache_from_collection()
        ordered = [self._deck_cache[k] for k in self._deck_order if k in self._deck_cache]
        return DeckCollection(ordered, client=self)


# Convenience functions mirroring alt.py
def list_decks_and_cards() -> dict[str, list[tuple[str, str]]]:
    client = RememberItClient()
    decks = client.decks()
    result: dict[str, list[tuple[str, str]]] = {}
    for deck in decks:
        rows: list[tuple[str, str]] = []
        for card in deck.cards:
            rows.append((card.front, card.back))
        result[deck.name] = rows
    return result


def add_demo(count: int = 3, deck: str = "CLI Demo") -> None:
    client = RememberItClient()
    if not client.session:
        raise RememberItError("Not logged in. Run rememberit.login(...) first.")
    decks = client.decks()
    try:
        target = decks[deck]
    except Exception:
        target = client.create_deck(deck)
    for i in range(count):
        client.add_card(target.id, f"CLI Front {i + 1}", f"CLI Back {i + 1}")


__all__ = [
    "RememberItClient",
    "RememberItError",
    "Session",
    "load_session",
    "save_session",
    "list_decks_and_cards",
    "add_demo",
]
