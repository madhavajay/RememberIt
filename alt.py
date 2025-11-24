import os
import sys
import json
import pathlib
from dataclasses import dataclass

from anki.collection import Collection
from anki.sync_pb2 import SyncAuth as ProtoSyncAuth
from anki.notes import Note
from anki.models import ModelManager

# Resolve paths
home = pathlib.Path.home()
store_dir = home / ".rememberit"
store_dir.mkdir(exist_ok=True)
col_path = store_dir / "collection.anki2"
config_path = store_dir / "config.json"


@dataclass
class Session:
    hkey: str
    endpoint: str
    username: str | None = None
    password: str | None = None


def load_session() -> Session | None:
    if not config_path.exists():
        return None
    return Session(**json.loads(config_path.read_text()))


def save_session(auth, user=None, pw=None) -> Session:
    sess = Session(
        hkey=auth.hkey,
        endpoint=auth.endpoint or "https://sync.ankiweb.net/",
        username=user,
        password=pw,
    )
    config_path.write_text(json.dumps(sess.__dict__, indent=2))
    return sess


def login(user: str | None = None, pw: str | None = None, endpoint: str | None = None) -> Session:
    user = user or os.getenv("ANKI_USER")
    pw = pw or os.getenv("ANKI_PASS")
    if not user or not pw:
        raise RuntimeError("Set ANKI_USER/ANKI_PASS or pass creds")
    tmp = store_dir / "_login.anki2"
    col = Collection(str(tmp))
    auth = col.sync_login(username=user, password=pw, endpoint=endpoint)
    col.close()
    tmp.unlink(missing_ok=True)
    return save_session(auth, user, pw)


def ensure_collection(sess: Session) -> Collection:
    exists = col_path.exists()
    col = Collection(str(col_path))
    if not exists:
        col.full_upload_or_download(
            auth=ProtoSyncAuth(hkey=sess.hkey, endpoint=sess.endpoint),
            server_usn=None,
            upload=False,
        )
    return col


def sync_down(sess: Session) -> None:
    def _run():
        col = ensure_collection(sess)
        col.sync_collection(
            auth=ProtoSyncAuth(hkey=sess.hkey, endpoint=sess.endpoint), sync_media=False
        )
        col.close()

    _run_in_thread(_run)


def sync_up(sess: Session) -> None:
    if not col_path.exists():
        raise RuntimeError("No local collection; run sync_down first")

    def _run():
        col = Collection(str(col_path))
        col.sync_collection(
            auth=ProtoSyncAuth(hkey=sess.hkey, endpoint=sess.endpoint), sync_media=False
        )
        col.close()

    _run_in_thread(_run)


def add_demo(sess: Session, count: int = 3, deck: str = "CLI Demo") -> None:
    if not col_path.exists():
        raise RuntimeError("No local collection; run sync_down first")
    col = Collection(str(col_path))
    mm: ModelManager = col.models
    m = mm.by_name("Basic")
    if not m:
        raise RuntimeError("Basic notetype not found in collection")
    # Create deck if missing
    deck_id = col.decks.id_for_name(deck)
    if deck_id is None:
        add_out = col.decks.add_normal_deck_with_name(deck)
        deck_id = add_out.id
    d = col.decks.get(deck_id)
    if isinstance(d, dict):

        class Obj:
            pass

        obj = Obj()
        obj.id = deck_id
        obj.name = deck
        d = obj
    for i in range(count):
        n = Note(col, model=m)
        n.fields[0] = f"CLI Front {i + 1}"
        n.fields[1] = f"CLI Back {i + 1}"
        col.add_note(n, deck_id=d.id)
    col.save()
    col.close()


def list_decks_and_cards() -> dict[str, list[tuple[str, str]]]:
    if not col_path.exists():
        raise RuntimeError("No local collection; run sync_down first")
    col = Collection(str(col_path))
    result: dict[str, list[tuple[str, str]]] = {}
    for deck in col.decks.all_names_and_ids():
        name = deck.name
        cards = []
        for cid in col.find_cards(f"deck:{name}"):
            c = col.get_card(cid)
            n = c.note()
            cards.append((n.fields[0], n.fields[1] if len(n.fields) > 1 else ""))
        result[name] = cards
    col.close()
    return result


# Run blocking backend calls in a worker thread to avoid warning in async notebooks.
def _run_in_thread(fn):
    import threading

    res = {}
    err = {}

    def wrapper():
        try:
            res["val"] = fn()
        except Exception as e:  # noqa: BLE001
            err["exc"] = e

    t = threading.Thread(target=wrapper)
    t.start()
    t.join()
    if "exc" in err:
        raise err["exc"]
    return res.get("val")
