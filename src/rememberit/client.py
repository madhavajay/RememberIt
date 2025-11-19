from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from pathlib import Path
import secrets
import gzip
from datetime import datetime, timezone
from pathlib import Path
import json

import httpx

from .config import Settings, load_settings, save_settings
from .proto import (
    decode_deck_list_info_response,
    decode_search_response,
    encode_deck_list_info_request,
    encode_add_or_update_request,
    encode_search_request,
    encode_remove_deck_request,
    encode_rename_deck_request,
    encode_create_deck_request,
)
from .models import (
    Card,
    CardCollection,
    Deck,
    DeckCollection,
    DeckListResult,
    CardSummary,
)

ANKIWEB_BASE_URL = "https://ankiweb.net"
DEFAULT_MODEL_ID = 1763445109221  # Basic (and reversed card) observed in UI
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36"
)

SYNC_BASE_URL = "https://sync12.ankiweb.net"
SYNC_PROTOCOL_VERSION = 11
SYNC_CLIENT_STRING = "25.09.2,3890e12c,macos"


class RememberItError(Exception):
    """Custom error class for RememberIt operations."""


@dataclass
class RememberItClient:
    def __init__(
        self,
        *,
        base_url: str = ANKIWEB_BASE_URL,
        settings: Optional[Settings] = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.settings = settings or load_settings()
        self._transport = transport
        self._client = self._build_client()
        self._debug_log_path = (
            Path(self.settings.debug_log_path).expanduser() if self.settings.debug_log_path else None
        )
        # Local caches for a friendlier OO interface
        self._deck_cache: dict[str, Deck] = {}
        self._deck_order: list[str] = []

    def _build_client(self) -> httpx.Client:
        ua = self.settings.user_agent or DEFAULT_USER_AGENT
        client = httpx.Client(
            base_url=self.base_url,
            headers={"User-Agent": ua},
            transport=self._transport,
            timeout=10.0,
            follow_redirects=True,
            # Leave HTTP/2 off to avoid requiring h2 dependency in minimal installs.
        )
        if self.settings.cookie_header:
            client.cookies.update(_cookie_header_to_dict(self.settings.cookie_header))
        return client

    def set_user_agent(self, user_agent: str, *, persist: bool = True) -> str:
        self.settings.user_agent = user_agent
        if persist:
            save_settings(self.settings)
        self._client = self._build_client()
        return user_agent

    def reset_user_agent(self, *, persist: bool = True) -> str:
        return self.set_user_agent(DEFAULT_USER_AGENT, persist=persist)

    def set_cookie_header(self, cookie_header: str, *, persist: bool = True) -> None:
        """Manually set cookies (from a raw Cookie header)."""
        self.settings.cookie_header = cookie_header
        if persist:
            save_settings(self.settings)
        self._client.cookies.clear()
        self._client.cookies.update(_cookie_header_to_dict(cookie_header))

    def set_cookie_header_ankiweb(self, cookie_header: str, *, persist: bool = True) -> None:
        self.settings.cookie_header_ankiweb = cookie_header
        if persist:
            save_settings(self.settings)

    def set_cookie_header_ankiuser(self, cookie_header: str, *, persist: bool = True) -> None:
        self.settings.cookie_header_ankiuser = cookie_header
        if persist:
            save_settings(self.settings)

    def set_debug_log(self, path: Optional[str], *, persist: bool = True) -> None:
        """
        Enable or disable debug logging of request/response headers and bodies.
        If path is None or empty, logging is disabled.
        """
        if path:
            log_path = Path(path).expanduser()
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self._debug_log_path = log_path
            self.settings.debug_log_path = str(log_path)
        else:
            self._debug_log_path = None
            self.settings.debug_log_path = ""
        if persist:
            save_settings(self.settings)


    def get_decks(self) -> Any:
        """
        Fetch deck tree information via /svc/decks/deck-list-info (protobuf over HTTP).
        """
        offset_minutes_east = int(
            datetime.now(timezone.utc).astimezone().utcoffset().total_seconds() / 60
        )
        # API expects minutes west of UTC, so invert the sign.
        minutes_west = -offset_minutes_east
        payload = encode_deck_list_info_request(minutes_west)

        response = self._request(
            "POST",
            "/svc/decks/deck-list-info",
            content=payload,
            headers={"Content-Type": "application/octet-stream"},
        )
        decoded = decode_deck_list_info_response(response.content)
        flattened: list[dict[str, Any]] = []
        if decoded.get("top_node"):
            self._flatten_decks(decoded["top_node"], prefix="", rows=flattened)
        decoded["decks_flat"] = flattened
        return DeckListResult(
            top_node=decoded.get("top_node"),
            current_deck_id=decoded.get("current_deck_id"),
            collection_size_bytes=decoded.get("collection_size_bytes"),
            media_size_bytes=decoded.get("media_size_bytes"),
            decks_flat=flattened,
            _client=self,
        )

    def list_decks(self) -> Dict[str, Any]:
        """Return a flattened view of decks along with the raw tree."""
        return self.get_decks()

    def sync(self) -> DeckCollection:
        """Download all decks and cards using the sync protocol."""
        return self.full_sync()

    def decks(self) -> DeckCollection:
        """Return cached decks, syncing if we have nothing yet."""
        if not self._deck_cache:
            return self.sync()
        ordered = [self._deck_cache[k] for k in self._deck_order if k in self._deck_cache]
        return DeckCollection(ordered, client=self)

    def login(self, email: str, password: str, *, persist: bool = True) -> str:
        """Authenticate with Anki sync server and return sync key."""
        import zstandard as zstd

        payload = {"u": email, "p": password}
        headers = self._build_sync_headers()
        # Use zstd compression (not gzip) and compact JSON
        json_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        cctx = zstd.ZstdCompressor()
        body = cctx.compress(json_bytes)

        resp = httpx.post(
            f"{SYNC_BASE_URL}/sync/hostKey",
            headers=headers,
            content=body,
            timeout=15.0,
        )
        resp.raise_for_status()

        # Response has zstd frame header followed by plain JSON
        # Extract JSON after the frame header (typically ~9 bytes)
        if b'{"key"' in resp.content:
            json_start = resp.content.find(b'{"key"')
            json_bytes_resp = resp.content[json_start:]
            json_end = json_bytes_resp.find(b'}') + 1
            json_str = json_bytes_resp[:json_end].decode('utf-8')
            data = json.loads(json_str)
        else:
            # Fallback to full zstd decode if format is different
            try:
                dctx = zstd.ZstdDecompressor()
                decompressed = dctx.decompress(resp.content)
                data = json.loads(decompressed)
            except Exception:
                data = self._decode_sync_json(resp.content)

        key = data.get("key")
        if not key:
            raise RememberItError("Sync hostKey response missing 'key'")

        # Save credentials and key
        if persist:
            self.settings.email = email
            self.settings.password = password
            self.settings.sync_key = key
            save_settings(self.settings)

        return key

    def get_sync_key(self) -> str | None:
        """Return cached sync key if available."""
        return self.settings.sync_key or None

    def logout(self) -> None:
        """Clear sync key and credentials."""
        self.settings.sync_key = ""
        self.settings.email = ""
        self.settings.password = ""
        save_settings(self.settings)

    def reset(self) -> None:
        """Delete all RememberIt data from ~/.rememberit folder."""
        from .config import _config_dir
        import shutil

        config_dir = _config_dir()
        if config_dir.exists():
            shutil.rmtree(config_dir)
        # Reset in-memory settings
        self.settings = Settings()
        self._deck_cache = {}
        self._deck_order = []

    # --- Minimal sync inspection helpers (v11) ---------------------------------
    def _build_sync_headers(self, sync_key: str | None = None) -> Dict[str, str]:
        header = {
            "v": SYNC_PROTOCOL_VERSION,
            "k": sync_key or "",
            "c": SYNC_CLIENT_STRING,
            "s": secrets.token_urlsafe(4),
        }
        return {
            "anki-sync": json.dumps(header, separators=(',', ':')),  # Compact JSON
            "Content-Type": "application/octet-stream",
            "Accept": "*/*",
            "User-Agent": self.settings.user_agent or DEFAULT_USER_AGENT,
        }

    def _decode_sync_json(self, payload: bytes) -> Dict[str, Any]:
        import zstandard as zstd

        errors: list[str] = []
        for attempt in ("zstd", "zstd-partial", "gzip", "plain"):
            try:
                if attempt == "zstd":
                    dctx = zstd.ZstdDecompressor()
                    text = dctx.decompress(payload).decode("utf-8")
                elif attempt == "zstd-partial":
                    # Response may have zstd frame header + plain JSON
                    if b'{"' in payload or b'[' in payload:
                        json_start = max(payload.find(b'{"'), payload.find(b'['))
                        if json_start > 0:
                            text = payload[json_start:].decode("utf-8", errors="ignore")
                        else:
                            continue
                    else:
                        continue
                elif attempt == "gzip":
                    text = gzip.decompress(payload).decode("utf-8")
                else:
                    text = payload.decode("utf-8")
                return json.loads(text)
            except Exception as err:  # noqa: BLE001 - bubble errors after attempts
                errors.append(f"{attempt}: {err}")
        raise RememberItError(f"Failed to decode sync JSON payload ({'; '.join(errors)})")

    def _maybe_gunzip(self, payload: bytes) -> bytes:
        import zstandard as zstd

        # Try zstd first (protocol v11+)
        try:
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(payload, max_output_size=50 * 1024 * 1024)  # 50MB max
        except Exception:
            pass
        # Fall back to gzip
        try:
            return gzip.decompress(payload)
        except Exception:
            return payload

    def _sync_request(self, path: str, sync_key: str, payload_obj: Dict[str, Any]) -> bytes:
        """Send a zstd-compressed JSON payload to /sync/* and return decompressed bytes."""
        import zstandard as zstd

        sync_url = f"{SYNC_BASE_URL}{path}"
        headers = self._build_sync_headers(sync_key)
        # Use zstd compression and compact JSON
        json_bytes = json.dumps(payload_obj, separators=(',', ':')).encode("utf-8")
        cctx = zstd.ZstdCompressor()
        body = cctx.compress(json_bytes)
        resp = httpx.post(sync_url, headers=headers, content=body, timeout=20.0)
        resp.raise_for_status()
        return self._maybe_gunzip(resp.content)

    def sync_meta_raw(self, sync_key: str, client_version: str = "anki,25.09.2 (3890e12c),mac:15.5") -> bytes:
        """Call /sync/meta and return decompressed raw bytes."""
        payload = {"v": SYNC_PROTOCOL_VERSION, "cv": client_version}
        return self._sync_request("/sync/meta", sync_key, payload)

    def sync_start_raw(self, sync_key: str, min_usn: int = 0, lnewer: bool = True, graves: Any = None) -> bytes:
        """Call /sync/start with simple JSON body (graves can be null)."""
        payload = {"minUsn": min_usn, "lnewer": lnewer, "graves": graves}
        return self._sync_request("/sync/start", sync_key, payload)

    def _sync_apply_changes(self, sync_key: str) -> Dict[str, Any]:
        """Call /sync/applyChanges with empty local changes to get server's decks/notetypes."""
        payload = {
            "changes": {
                "models": [],
                "decks": [[], []],  # DecksAndConfig: [decks, config]
                "tags": [],
            }
        }
        resp_bytes = self._sync_request("/sync/applyChanges", sync_key, payload)
        return self._decode_sync_json(resp_bytes)

    def _sync_chunk(self, sync_key: str) -> Dict[str, Any]:
        """Call /sync/chunk to get a chunk of cards/notes."""
        payload = {"_pad": None}  # EmptyInput
        resp_bytes = self._sync_request("/sync/chunk", sync_key, payload)
        return self._decode_sync_json(resp_bytes)

    def _sync_finish(self, sync_key: str) -> int:
        """Call /sync/finish to complete sync."""
        payload = {"_pad": None}  # EmptyInput
        resp_bytes = self._sync_request("/sync/finish", sync_key, payload)
        # Returns TimestampMillis - try to decode as JSON first
        try:
            result = self._decode_sync_json(resp_bytes)
            return int(result) if not isinstance(result, dict) else 0
        except Exception:
            # Fallback to plain text
            return int(resp_bytes.decode("utf-8").strip())

    def full_sync(self) -> DeckCollection:
        """Download entire collection using /sync/download and parse SQLite."""
        if not self.settings.sync_key:
            raise RememberItError("Not logged in. Call login() first.")

        import sqlite3
        import tempfile
        from pathlib import Path

        sync_key = self.settings.sync_key

        # Download the full collection as SQLite database
        payload = {"_pad": None}  # EmptyInput
        db_bytes = self._sync_request("/sync/download", sync_key, payload)

        # Write to temporary file and open as SQLite
        with tempfile.NamedTemporaryFile(delete=False, suffix=".anki2") as tmp:
            tmp.write(db_bytes)
            tmp_path = tmp.name

        try:
            conn = sqlite3.connect(tmp_path)
            conn.row_factory = sqlite3.Row

            # Get all decks (from separate decks table in newer schema)
            deck_map: Dict[int, Dict[str, Any]] = {}
            try:
                # Try newer schema with decks table
                for row in conn.execute("SELECT id, name FROM decks"):
                    deck_id = row["id"]
                    deck_name = row["name"]
                    deck_map[deck_id] = {
                        "id": deck_id,
                        "name": deck_name,
                        "path": deck_name,
                    }
            except sqlite3.OperationalError:
                # Fall back to older schema with decks column in col table
                decks_json = conn.execute("SELECT decks FROM col").fetchone()[0]
                if decks_json:
                    decks_data = json.loads(decks_json)
                    for deck_id_str, deck_info in decks_data.items():
                        deck_id = int(deck_id_str)
                        deck_map[deck_id] = {
                            "id": deck_id,
                            "name": deck_info.get("name", ""),
                            "path": deck_info.get("name", ""),
                        }

            # Get all notes
            note_map: Dict[int, Dict[str, Any]] = {}
            for row in conn.execute("SELECT id, flds FROM notes"):
                note_id = row["id"]
                fields = row["flds"]  # Fields separated by \x1f
                note_map[note_id] = {"id": note_id, "fields": fields}

            # Get all cards and group by deck
            deck_cards: Dict[int, list[Card]] = {}
            for row in conn.execute("SELECT id, nid, did FROM cards"):
                card_id = row["id"]
                note_id = row["nid"]
                deck_id = row["did"]

                # Get note fields
                note = note_map.get(note_id, {})
                fields = note.get("fields", "").split("\x1f")
                front = fields[0] if len(fields) > 0 else ""
                back = fields[1] if len(fields) > 1 else ""

                card = Card(
                    id=card_id,
                    front=front,
                    back=back,
                    raw_text=f"{front}\x1f{back}",
                    edit_url=f"{ANKIWEB_BASE_URL}/edit/{note_id}",
                    deck=None,
                    _client=self,
                )

                if deck_id not in deck_cards:
                    deck_cards[deck_id] = []
                deck_cards[deck_id].append(card)

            conn.close()

            # Create Deck objects
            decks: list[Deck] = []
            for deck_id, deck_info in deck_map.items():
                cards = CardCollection(deck_cards.get(deck_id, []))
                deck = Deck(
                    id=deck_id,
                    name=deck_info["name"],
                    path=deck_info["path"],
                    counts={"total": len(cards)},
                    cards=cards,
                    _client=self,
                )
                for card in cards:
                    card.deck = deck
                decks.append(deck)

            # Cache the decks
            self._deck_cache = {self._deck_key_from_deck(d): d for d in decks}
            self._deck_order = [self._deck_key_from_deck(d) for d in decks]

            return DeckCollection(decks, client=self)

        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)

    def search_cards(self, query: str, deck: Deck | None = None) -> list[Card]:
        payload = encode_search_request(query)
        response = self._request(
            "POST",
            "/svc/search/search",
            content=payload,
            headers={
                "Content-Type": "application/octet-stream",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/search",
                "Accept": "*/*",
            },
        )
        # Try HTML parse if server returns HTML, else try to parse text content.
        ctype = response.headers.get("Content-Type", "")
        if "application/octet-stream" in ctype or response.content.startswith(b"\n"):
            try:
                rows = decode_search_response(response.content)
                cards: list[Card] = []
                for row in rows:
                    front, back = _split_front_back(row.get("text", ""))
                    note_id = row.get("note_id") or None
                    cards.append(
                        Card(
                            id=note_id,
                            front=front,
                            back=back,
                            raw_text=row.get("text", ""),
                            edit_url=f"{self.base_url}/edit/{note_id}" if note_id is not None else None,
                            deck=deck,
                            _client=self,
                        )
                    )
                return cards
            except Exception:
                pass
        # HTML fallbacks
        if "text/html" in ctype:
            summaries = _parse_search_html(response.text)
        else:
            try:
                text = response.content.decode("utf-8", errors="ignore")
                if "<table" in text:
                    summaries = _parse_search_html(text)
                else:
                    summaries = []
            except Exception:
                summaries = []
        if summaries:
            cards: list[Card] = []
            for summary in summaries:
                front, back = _split_front_back(summary.text)
                cards.append(
                    Card(
                        id=int(summary.id) if summary.id is not None else None,
                        front=front,
                        back=back,
                        raw_text=summary.text,
                        edit_url=summary.edit_url,
                        deck=deck,
                        _client=self,
                    )
                )
            return cards
        # Fallback: return raw content summarized as a single Card
        return [
            Card(
                id=None,
                front="",
                back="",
                raw_text=f"search response bytes ({len(response.content)} bytes, base64): "
                f"{response.content[:60].hex()}...",
                edit_url=None,
                deck=deck,
                _client=self,
            )
        ]

    def add_card(
        self, deck_id: int, front: str, back: str, tags: str = "", model_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add a card by modifying the collection and uploading."""
        import time
        import uuid

        model = model_id if model_id is not None else DEFAULT_MODEL_ID

        def add_note_and_card(conn):
            # Generate IDs
            now = int(time.time())
            now_ms = int(time.time() * 1000)
            note_id = now_ms
            card_id = now_ms + 1
            guid = str(uuid.uuid4())[:8]  # Short GUID like Anki uses

            # Fields separated by \x1f
            fields = f"{front}\x1f{back}"

            # Insert note
            conn.execute(
                """INSERT INTO notes (id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (note_id, guid, model, now, -1, tags, fields, "", 0, 0, "")
            )

            # Insert card (ord=0 for first template, queue=0 for new, type=0 for learning)
            conn.execute(
                """INSERT INTO cards (id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses, left, odue, odid, flags, data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (card_id, note_id, deck_id, 0, now, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "")
            )

        self._modify_and_upload_collection(add_note_and_card)
        return {"status_code": 200}

    def remove_deck(self, deck: Deck | str | int) -> Dict[str, Any]:
        """
        Delete a deck by Deck object, name/path, or id using /svc/decks/remove-deck (protobuf).
        """
        deck_obj: Deck
        if isinstance(deck, Deck):
            deck_obj = deck
        else:
            # resolve from cached decks or fetch fresh
            collection = self.decks()
            try:
                deck_obj = collection[deck]  # type: ignore[index]
            except Exception:
                raise RememberItError(f"Deck not found: {deck}")

        payload = encode_remove_deck_request(int(deck_obj.id))
        headers = {
            "Content-Type": "application/octet-stream",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/decks",
            "Accept": "*/*",
        }
        response = self._request("POST", "/svc/decks/remove-deck", content=payload, headers=headers)
        # Drop from local cache
        key = self._deck_key_from_deck(deck_obj)
        self._deck_cache.pop(key, None)
        self._deck_order = [k for k in self._deck_order if k != key]
        return {"status_code": response.status_code}

    def rename_deck(self, deck: Deck | str | int, new_name: str) -> Dict[str, Any]:
        """
        Rename a deck by Deck object, name/path, or id using /svc/decks/rename-deck (protobuf).
        """
        deck_obj: Deck
        if isinstance(deck, Deck):
            deck_obj = deck
        else:
            collection = self.decks()
            try:
                deck_obj = collection[deck]  # type: ignore[index]
            except Exception:
                raise RememberItError(f"Deck not found: {deck}")

        payload = encode_rename_deck_request(int(deck_obj.id), new_name)
        headers = {
            "Content-Type": "application/octet-stream",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/decks",
            "Accept": "*/*",
        }
        response = self._request("POST", "/svc/decks/rename-deck", content=payload, headers=headers)

        # Update cache and object
        old_key = self._deck_key_from_deck(deck_obj)
        deck_obj.name = new_name
        deck_obj.path = new_name
        new_key = self._deck_key_from_deck(deck_obj)
        self._deck_cache.pop(old_key, None)
        self._deck_cache[new_key] = deck_obj
        self._deck_order = [new_key if k == old_key else k for k in self._deck_order]
        return {"status_code": response.status_code}

    def _modify_and_upload_collection(self, modifier_fn):
        """Download collection, modify it via callback, and upload back."""
        import sqlite3
        import tempfile
        from pathlib import Path
        import time

        if not self.settings.sync_key:
            raise RememberItError("Not logged in. Call login() first.")

        sync_key = self.settings.sync_key

        # Download current collection
        payload = {"_pad": None}
        db_bytes = self._sync_request("/sync/download", sync_key, payload)

        # Write to temp file and modify
        with tempfile.NamedTemporaryFile(delete=False, suffix=".anki2", mode="wb") as tmp:
            tmp.write(db_bytes)
            tmp_path = tmp.name

        try:
            conn = sqlite3.connect(tmp_path)

            # Register Anki's custom collation for case-insensitive comparison
            conn.create_collation("unicase", lambda x, y: (x.lower() > y.lower()) - (x.lower() < y.lower()))

            # Call modifier function to make changes
            modifier_fn(conn)

            # Update collection modified timestamp
            conn.execute("UPDATE col SET mod = ?", (int(time.time() * 1000),))
            conn.commit()
            conn.close()

            # Read modified database
            with open(tmp_path, "rb") as f:
                modified_db = f.read()

            # Upload modified collection
            import zstandard as zstd
            cctx = zstd.ZstdCompressor()
            compressed = cctx.compress(modified_db)

            headers = self._build_sync_headers(sync_key)
            headers["Content-Type"] = "application/octet-stream"

            resp = httpx.post(
                f"{SYNC_BASE_URL}/sync/upload",
                headers=headers,
                content=compressed,
                timeout=60.0,
            )
            resp.raise_for_status()

            # Clear cache and resync
            self._deck_cache = {}
            self._deck_order = []
            return self.sync()

        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def create_deck(self, name: str) -> Deck:
        """Create a new deck by modifying the collection and uploading."""
        import time

        def add_deck(conn):
            # Generate new deck ID (timestamp in milliseconds)
            deck_id = int(time.time() * 1000)

            # Insert into decks table with proper protobuf blobs
            # common: minimal protobuf structure for deck settings
            # kind: b'\n\x02\x08\x01' for normal deck (not filtered)
            conn.execute(
                "INSERT INTO decks (id, name, mtime_secs, usn, common, kind) VALUES (?, ?, ?, ?, ?, ?)",
                (deck_id, name, int(time.time()), -1, b'\x08\x01\x10\x01', b'\n\x02\x08\x01')
            )

        collection = self._modify_and_upload_collection(add_deck)
        try:
            return collection[name]
        except Exception:
            raise RememberItError(f"Deck '{name}' not found after creation")

    def load_deck(
        self,
        path: str | Path | Mapping[str, Any],
        *,
        deck_name: str | None = None,
        model_id: int = DEFAULT_MODEL_ID,
        replace: bool = False,
    ) -> Deck:
        """
        Load a deck from a JSON file or mapping (schema: {name?, deck_id?, cards:[{front,back,tags?,note_id?}]}).
        Adds new cards and updates existing ones (when note_id provided) and avoids duplicate adds when
        front/back already exist. Syncs the deck before and after.
        """
        if isinstance(path, Mapping):
            data = dict(path)
        else:
            file_path = Path(path)
            if not file_path.exists():
                raise RememberItError(f"Deck file not found: {path}")
            if file_path.suffix.lower() != ".json":
                raise RememberItError("Only JSON import is supported right now (provide a .json file)")
            data = json.loads(file_path.read_text(encoding="utf-8"))
        cards_data = data.get("cards")
        if not isinstance(cards_data, list):
            raise RememberItError("Deck JSON must contain a 'cards' array")

        target_name = deck_name or data.get("name")
        target_id = data.get("deck_id")

        deck_obj = self._resolve_deck_or_create(target_id=target_id, target_name=target_name)
        if deck_obj is None:
            names = [d.name for d in self.decks()]
            raise RememberItError(
                f"Deck not found. Looked for id={target_id} name={target_name!r}. "
                f"Available decks: {names}. Please create the deck in AnkiWeb UI first."
            )

        # Ensure we have current cards to dedupe/upsert against
        deck_obj.sync()
        existing_cards = list(deck_obj.cards)
        by_id = {c.id: c for c in existing_cards if c.id is not None}
        by_front_back = {(c.front, c.back): c for c in existing_cards}
        by_front = {}
        for c in existing_cards:
            by_front.setdefault(c.front, c)

        # Deduplicate incoming payload by (front, back) to avoid double-add in one call
        seen_fb: set[tuple[str, str]] = set()
        for card in cards_data:
            front = card.get("front", "")
            back = card.get("back", "")
            tags = card.get("tags", "")
            note_id = card.get("note_id")
            key_fb = (front, back)
            if key_fb in seen_fb:
                continue
            seen_fb.add(key_fb)

            if note_id and note_id in by_id:
                existing = by_id[note_id]
                if replace or existing.front != front or existing.back != back:
                    self.update_card(
                        note_id=note_id,
                        front=front,
                        back=back,
                        tags=tags,
                        model_id=model_id,
                        deck_id=deck_obj.id,
                    )
                continue

            if key_fb in by_front_back:
                # Already present with same front/back: skip to remain idempotent
                continue

            # Same front, different back? update that note_id instead of adding
            if front in by_front and by_front[front].id is not None:
                self.update_card(
                    note_id=by_front[front].id,
                    front=front,
                    back=back,
                    tags=tags,
                    model_id=model_id,
                    deck_id=deck_obj.id,
                )
                continue

            # New card
            self.add_card(deck_id=deck_obj.id, front=front, back=back, tags=tags, model_id=model_id)

        deck_obj.sync()
        return deck_obj

    def _resolve_deck(self, target_id: Any, target_name: str | None) -> Deck | None:
        collection = self.sync()
        if target_id is not None:
            try:
                return collection[target_id]  # type: ignore[index]
            except Exception:
                pass
        if target_name:
            try:
                return collection[target_name]  # type: ignore[index]
            except Exception:
                pass
        return None

    def _resolve_deck_or_create(self, target_id: Any, target_name: str | None) -> Deck | None:
        deck = self._resolve_deck(target_id, target_name)
        if deck:
            return deck
        if not target_name:
            return None
        try:
            return self.create_deck(target_name)
        except Exception:
            return None

    def update_card(
        self,
        note_id: int,
        front: str,
        back: str,
        tags: str = "",
        model_id: Optional[int] = None,
        deck_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload = encode_add_or_update_request(
            front=front, back=back, tags=tags, note_id=note_id, model_id=model_id, deck_id=deck_id
        )
        primary = "https://ankiuser.net"
        headers = {
            "Content-Type": "application/octet-stream",
            "Origin": primary,
            "Referer": f"{primary}/edit/{note_id}",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-CH-UA": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"macOS"',
        }
        try:
            response = self._request(
                "POST",
                f"{primary}/svc/editor/add-or-update",
                content=payload,
                headers=headers,
            )
        except RememberItError as err:
            if "404" in str(err):
                fallback = ANKIWEB_BASE_URL
                response = self._request(
                    "POST",
                    f"{fallback}/svc/editor/add-or-update",
                    content=payload,
                    headers={**headers, "Origin": fallback, "Referer": f"{fallback}/edit/{note_id}"},
                )
            else:
                raise
        return {"status_code": response.status_code}

    def _deck_key(self, row: Mapping[str, Any]) -> str:
        return str(row.get("path") or row.get("name") or row.get("id") or "")

    def _deck_key_from_deck(self, deck: Deck) -> str:
        return str(deck.path or deck.name or deck.id or "")

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        merged_headers = headers.copy() if headers else {}

        # Add anki-sync header with sync key if we have one
        if self.settings.sync_key and "anki-sync" not in {k.lower() for k in merged_headers}:
            sync_header = self._build_sync_headers(self.settings.sync_key)
            merged_headers["anki-sync"] = sync_header["anki-sync"]

        # Host-specific cookie support
        host = ""
        if isinstance(url, str):
            if url.startswith("http"):
                host = httpx.URL(url).host or ""
            else:
                host = httpx.URL(self.base_url + url).host or ""
        cookie = None
        if host.endswith("ankiuser.net") and self.settings.cookie_header_ankiuser:
            cookie = self.settings.cookie_header_ankiuser
        elif host.endswith("ankiweb.net") and self.settings.cookie_header_ankiweb:
            cookie = self.settings.cookie_header_ankiweb
        elif self.settings.cookie_header:
            cookie = self.settings.cookie_header
        if cookie and "Cookie" not in merged_headers:
            merged_headers["Cookie"] = cookie
        if "user-agent" not in {k.lower() for k in merged_headers}:
            merged_headers.setdefault("User-Agent", self._client.headers.get("User-Agent", DEFAULT_USER_AGENT))
        merged_headers.setdefault("Accept", "*/*")
        merged_headers.setdefault("Accept-Encoding", "gzip, deflate, br, zstd")
        merged_headers.setdefault("Connection", "keep-alive")
        try:
            response = self._client.request(method, url, headers=merged_headers, **kwargs)
            response.raise_for_status()
            self._log_exchange(method, url, merged_headers, kwargs, response)
            return response
        except httpx.HTTPStatusError as err:
            # Log the failed exchange for debugging
            self._log_exchange(method, url, merged_headers, kwargs, err.response)
            # Provide helpful message for 403 errors
            if err.response.status_code == 403:
                msg = (
                    "AnkiWeb API requires browser cookies. "
                    "Login to ankiweb.net in your browser, then:\n"
                    '  1. Open DevTools (F12) → Application → Cookies\n'
                    '  2. Copy the "ankiweb" cookie value\n'
                    '  3. Run: rememberit.set_cookie_header_ankiweb("ankiweb=<value>; has_auth=1")'
                )
                raise RememberItError(msg) from err
            raise RememberItError(
                f"AnkiWeb request failed: {err.response.status_code} {err.response.reason_phrase}"
            ) from err
        except httpx.HTTPError as err:
            raise RememberItError(f"Network error contacting AnkiWeb: {err}") from err

    def close(self) -> None:
        self._client.close()

    def _log_exchange(
        self,
        method: str,
        url: str,
        req_headers: Dict[str, str],
        req_kwargs: Dict[str, Any],
        response: httpx.Response,
    ) -> None:
        if not self._debug_log_path:
            return
        try:
            entry = {
                "method": method,
                "url": url,
                "request_headers": {**self._client.headers, **(req_headers or {})},
                "request_body_len": len(req_kwargs.get("content", b"") or b""),
                "request_body_preview": _preview_bytes(req_kwargs.get("content")),
                "response_status": response.status_code,
                "response_headers": dict(response.headers),
                "response_body_len": len(response.content),
                "response_body_preview": _preview_bytes(response.content),
            }
            with self._debug_log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False))
                fh.write("\n")
        except Exception:
            # Logging failures should not break main flow
            pass

    def _flatten_decks(self, node, prefix: str, rows: list) -> None:
        path = prefix + node.name if node.name else prefix.rstrip("::")
        rows.append(
            {
                "id": node.id,
                "name": node.name,
                "path": path,
                "level": node.level,
                "new": node.new_count,
                "learn": node.learn_count,
                "review": node.review_count,
                "total": node.total_in_deck,
                "total_incl_children": node.total_including_children,
            }
        )
        for child in node.children:
            child_prefix = (path + "::") if path else ""
            self._flatten_decks(child, child_prefix, rows)


__all__ = [
    "DEFAULT_USER_AGENT",
    "ANKIWEB_BASE_URL",
    "DeckCollection",
    "Card",
    "CardCollection",
    "RememberItClient",
    "RememberItError",
]


def _split_front_back(text: str) -> tuple[str, str]:
    if " / " in text:
        front, back = text.split(" / ", 1)
        return front.strip(), back.strip()
    return text.strip(), ""


def _cookie_header_to_dict(cookie_header: str) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    for part in cookie_header.split(";"):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def _preview_bytes(data: Any, limit: int = 2000) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        if len(data) > limit:
            return data[:limit] + "...(truncated)"
        return data
    if isinstance(data, (bytes, bytearray)):
        if len(data) > limit:
            return data[:limit].decode(errors="replace") + "...(truncated)"
        return data.decode(errors="replace")
    return repr(data)


def _parse_search_html(html: str) -> list[CardSummary]:
    """
    Parse the simple HTML table returned by /svc/search/search.
    Expected rows with an <a href=".../edit/<id>">Edit</a> followed by text.
    """
    results: list[CardSummary] = []
    # A loose extractor based on the observed table structure
    import re

    row_pattern = re.compile(r'href="([^"]*?/edit/([\d]+))"[^>]*>Edit</a>\\s*</td>\\s*<td>(.*?)</td>', re.DOTALL)
    for m in row_pattern.finditer(html):
        edit_url, card_id, text = m.groups()
        clean_text = re.sub(r"\\s+", " ", text).strip()
        results.append(CardSummary(id=card_id, edit_url=edit_url, text=clean_text))
    return results
