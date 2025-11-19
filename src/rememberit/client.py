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

    def login(self, email: str, password: str, *, persist: bool = True) -> Dict[str, Any]:
        """Log in to AnkiWeb with credentials and persist them."""
        self.settings.email = email
        self.settings.password = password
        if persist:
            save_settings(self.settings)

        # Grab a fresh session cookie first
        self._request("GET", "/account/login")

        payload = f"{email} {password}".encode("utf-8")
        headers = {
            "Content-Type": "application/octet-stream",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/account/login",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = self._request(
            "POST",
            "/svc/account/login",
            content=payload,
            headers=headers,
        )

        return {"status_code": response.status_code, "url": str(response.url)}

    def sync(self) -> Dict[str, Any]:
        """
        Trigger a sync with AnkiWeb.

        The exact endpoint can change; this method uses a common sync path but may need
        adjustment once we inspect live responses.
        """
        response = self._request("GET", "/sync/")
        try:
            return response.json()
        except ValueError:
            return {"status_code": response.status_code, "content": response.text}

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
        """
        Load all decks and their cards into local objects for notebook-friendly access.
        """
        deck_list = self.get_decks()
        decks: list[Deck] = []

        for row in deck_list.decks_flat:
            deck = self._deck_cache.get(self._deck_key(row)) or Deck.from_row(row, client=self)
            deck.update_from_row(row)
            decks.append(deck)

        # Populate cards per deck (one search call per deck)
        for deck in decks:
            deck.cards = CardCollection(self.search_cards(f"deck:{deck.path or deck.name}", deck=deck))

        self._deck_cache = {self._deck_key_from_deck(d): d for d in decks}
        self._deck_order = [self._deck_key_from_deck(d) for d in decks]
        return DeckCollection(decks, client=self)

    def decks(self) -> DeckCollection:
        """Return cached decks, syncing if we have nothing yet."""
        if not self._deck_cache:
            return self.sync()
        ordered = [self._deck_cache[k] for k in self._deck_order if k in self._deck_cache]
        return DeckCollection(ordered, client=self)

    def sync_host_key(self, email: str, password: str) -> str:
        """
        Perform sync login (/sync/hostKey) to obtain a sync key for the collection sync protocol.
        WARNING: sends credentials directly to sync12.ankiweb.net.
        """
        sync_url = "https://sync12.ankiweb.net/sync/hostKey"
        sync_header = {
            "v": 11,
            "k": "",
            "c": "25.09.2,rememberit-sync,python-httpx",
            "s": secrets.token_urlsafe(4),
        }
        headers = {
            "anki-sync": json.dumps(sync_header),
            "Content-Type": "application/octet-stream",
            "Accept": "*/*",
        }
        body = json.dumps({"u": email, "p": password}).encode("utf-8")
        gz_body = gzip.compress(body)
        resp = httpx.post(sync_url, headers=headers, content=gz_body, timeout=15.0)
        resp.raise_for_status()
        try:
            data = json.loads(gzip.decompress(resp.content))
        except Exception as err:
            raise RememberItError(f"Failed to decode sync hostKey response: {err}") from err
        key = data.get("key")
        if not key:
            raise RememberItError("Sync hostKey response missing 'key'")
        return key

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

    def get_deck(self, deck_id: str) -> Any:
        response = self._request("GET", f"/api/decks/{deck_id}")
        try:
            return response.json()
        except ValueError as err:  # pragma: no cover - defensive
            raise RememberItError("Unexpected response format for deck") from err

    def update_deck(self, deck_id: str, payload: Dict[str, Any]) -> Any:
        response = self._request("PATCH", f"/api/decks/{deck_id}", json=payload)
        try:
            return response.json()
        except ValueError:
            return {"status_code": response.status_code, "content": response.text}

    def delete_deck(self, deck_id: str) -> Dict[str, Any]:
        response = self._request("DELETE", f"/api/decks/{deck_id}")
        return {"status_code": response.status_code}

    def add_card(
        self, deck_id: int, front: str, back: str, tags: str = "", model_id: Optional[int] = None
    ) -> Dict[str, Any]:
        # model_id is required by server; fall back to typical Basic (and reversed card) id if not provided
        model = model_id if model_id is not None else DEFAULT_MODEL_ID
        payload = encode_add_or_update_request(
            front=front, back=back, tags=tags, model_id=model, deck_id=deck_id
        )
        primary = "https://ankiuser.net"
        headers = {
            "Content-Type": "application/octet-stream",
            "Origin": primary,
            "Referer": f"{primary}/add",
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
            # If primary host returns 404, retry on ankiweb.net as a fallback.
            if "404" in str(err):
                fallback = ANKIWEB_BASE_URL
                response = self._request(
                    "POST",
                    f"{fallback}/svc/editor/add-or-update",
                    content=payload,
                    headers={**headers, "Origin": fallback, "Referer": f"{fallback}/add"},
                )
            else:
                raise
        return {"status_code": response.status_code}

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

    def create_deck(self, name: str) -> Deck:
        """
        Create a new deck via /svc/decks/create-deck (protobuf), then resync and return it.
        """
        payload = encode_create_deck_request(name)
        headers = {
            "Content-Type": "application/octet-stream",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/decks",
            "Accept": "*/*",
        }
        self._request("POST", "/svc/decks/create-deck", content=payload, headers=headers)
        collection = self.sync()
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
