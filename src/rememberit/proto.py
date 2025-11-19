from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory


def _build_descriptors() -> descriptor_pool.DescriptorPool:
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "rememberit_decks.proto"
    file_proto.package = "rememberit"
    file_proto.syntax = "proto3"

    # DeckNode
    deck_node = file_proto.message_type.add()
    deck_node.name = "DeckNode"
    deck_node.field.add(
        name="deck_id",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )
    deck_node.field.add(
        name="name",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    deck_node.field.add(
        name="level",
        number=4,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="collapsed",
        number=5,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_BOOL,
    )
    deck_node.field.add(
        name="review_count",
        number=6,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="learn_count",
        number=7,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="new_count",
        number=8,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="intraday_learning",
        number=9,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="interday_learning_uncapped",
        number=10,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="new_uncapped",
        number=11,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="review_uncapped",
        number=12,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="total_in_deck",
        number=13,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="total_including_children",
        number=14,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
    )
    deck_node.field.add(
        name="filtered",
        number=16,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_BOOL,
    )
    deck_node.field.add(
        name="children",
        number=3,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name="DeckNode",
    )

    # DeckListInfoRequest
    req = file_proto.message_type.add()
    req.name = "DeckListInfoRequest"
    req.field.add(
        name="minutes_west_of_utc",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT32,
    )

    # DeckListInfoResponse
    resp = file_proto.message_type.add()
    resp.name = "DeckListInfoResponse"
    resp.field.add(
        name="top_node",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name="DeckNode",
    )
    resp.field.add(
        name="current_deck_id",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )
    resp.field.add(
        name="collection_size_bytes",
        number=3,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT64,
    )
    resp.field.add(
        name="media_size_bytes",
        number=4,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_UINT64,
    )

    # NoteId
    note_id_msg = file_proto.message_type.add()
    note_id_msg.name = "NoteId"
    note_id_msg.field.add(
        name="id",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )

    # ModelSelection (note type id + apply_all)
    model_sel_msg = file_proto.message_type.add()
    model_sel_msg.name = "ModelSelection"
    model_sel_msg.field.add(
        name="id",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )
    model_sel_msg.field.add(
        name="deck_id",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )

    # AddOrUpdateRequest
    add_or_update = file_proto.message_type.add()
    add_or_update.name = "AddOrUpdateRequest"
    add_or_update.field.add(
        name="fields",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    add_or_update.field.add(
        name="tags",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    add_or_update.field.add(
        name="model",
        number=3,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name="ModelSelection",
    )
    add_or_update.field.add(
        name="note",
        number=4,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name="NoteId",
    )

    # SearchRequest (for /svc/search/search)
    search_req = file_proto.message_type.add()
    search_req.name = "SearchRequest"
    search_req.field.add(
        name="query",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )

    # SearchResponse (for /svc/search/search)
    search_result = file_proto.message_type.add()
    search_result.name = "SearchResult"
    search_result.field.add(
        name="note_id",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )
    search_result.field.add(
        name="text",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )

    search_resp = file_proto.message_type.add()
    search_resp.name = "SearchResponse"
    search_resp.field.add(
        name="results",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name="SearchResult",
    )

    # RemoveDeckRequest (for /svc/decks/remove-deck)
    remove_deck = file_proto.message_type.add()
    remove_deck.name = "RemoveDeckRequest"
    remove_deck.field.add(
        name="deck_id",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )

    # RenameDeckRequest (for /svc/decks/rename-deck)
    rename_deck = file_proto.message_type.add()
    rename_deck.name = "RenameDeckRequest"
    rename_deck.field.add(
        name="deck_id",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
    )
    rename_deck.field.add(
        name="name",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )

    # CreateDeckRequest (for /svc/decks/create-deck)
    create_deck = file_proto.message_type.add()
    create_deck.name = "CreateDeckRequest"
    create_deck.field.add(
        name="name",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)
    return pool


_POOL = _build_descriptors()


def _get_message_class(full_name: str):
    desc = _POOL.FindMessageTypeByName(full_name)
    factory = message_factory.MessageFactory(_POOL)
    try:
        return factory.GetPrototype(desc)  # protobuf < 5.0
    except AttributeError:
        try:
            return message_factory.GetMessageClass(desc)  # type: ignore[attr-defined]
        except AttributeError:
            messages = message_factory.GetMessages([desc.file])
            return messages[full_name]


DeckNodeMessage = _get_message_class("rememberit.DeckNode")
DeckListInfoRequest = _get_message_class("rememberit.DeckListInfoRequest")
DeckListInfoResponse = _get_message_class("rememberit.DeckListInfoResponse")
AddOrUpdateRequest = _get_message_class("rememberit.AddOrUpdateRequest")
ModelSelection = _get_message_class("rememberit.ModelSelection")
NoteId = _get_message_class("rememberit.NoteId")
SearchRequest = _get_message_class("rememberit.SearchRequest")
SearchResult = _get_message_class("rememberit.SearchResult")
SearchResponse = _get_message_class("rememberit.SearchResponse")
RemoveDeckRequest = _get_message_class("rememberit.RemoveDeckRequest")
RenameDeckRequest = _get_message_class("rememberit.RenameDeckRequest")
CreateDeckRequest = _get_message_class("rememberit.CreateDeckRequest")


@dataclass
class DeckNode:
    id: int
    name: str
    level: int
    collapsed: bool
    review_count: int
    learn_count: int
    new_count: int
    intraday_learning: int
    interday_learning_uncapped: int
    new_uncapped: int
    review_uncapped: int
    total_in_deck: int
    total_including_children: int
    filtered: bool
    children: List["DeckNode"] = field(default_factory=list)

    def _repr_markdown_(self) -> str:
        # Simple markdown row representation
        return f"|{self.id}|{self.name or '(root)'}|{self.level}|{self.new_count}|{self.learn_count}|{self.review_count}|{self.total_in_deck}|{self.total_including_children}|"


def encode_deck_list_info_request(minutes_west_of_utc: Optional[int]) -> bytes:
    message = DeckListInfoRequest()
    if minutes_west_of_utc is not None:
        message.minutes_west_of_utc = minutes_west_of_utc
    return message.SerializeToString()


def decode_deck_list_info_response(payload: bytes) -> Dict[str, object]:
    message = DeckListInfoResponse.FromString(payload)
    present = {fd.name for fd, _ in message.ListFields()}
    top_node = (
        _normalize_deck_node(message.top_node) if message.HasField("top_node") else None
    )
    return {
        "top_node": top_node,
        "current_deck_id": message.current_deck_id if "current_deck_id" in present else None,
        "collection_size_bytes": message.collection_size_bytes
        if "collection_size_bytes" in present
        else None,
        "media_size_bytes": message.media_size_bytes if "media_size_bytes" in present else None,
    }


def encode_add_or_update_request(
    front: str,
    back: str,
    tags: str = "",
    model_id: Optional[int] = None,
    note_id: Optional[int] = None,
    deck_id: Optional[int] = None,
) -> bytes:
    """
    Build the payload for /svc/editor/add-or-update.
    - For add: provide model_id (note type id), front, back, tags
    - For update: provide note_id, front, back, tags (model_id optional)
    """
    msg = AddOrUpdateRequest()
    msg.fields.extend([front, back])
    if tags:
        msg.tags = tags
    if model_id is not None:
        msg.model.id = model_id
    if deck_id is not None:
        msg.model.deck_id = deck_id
    if note_id is not None:
        msg.note.id = note_id
    return msg.SerializeToString()


def encode_search_request(query: str) -> bytes:
    msg = SearchRequest()
    msg.query = query
    return msg.SerializeToString()


def decode_search_response(payload: bytes) -> list[dict]:
    """
    Decode /svc/search/search payload into a simple list of dict rows:
    - note_id: int
    - text: str (front/back joined with " / ")
    """
    message = SearchResponse.FromString(payload)
    rows = []
    for res in message.results:
        rows.append(
            {
                "note_id": res.note_id,
                "text": res.text,
            }
        )
    return rows


def encode_remove_deck_request(deck_id: int) -> bytes:
    msg = RemoveDeckRequest()
    msg.deck_id = deck_id
    return msg.SerializeToString()


def encode_rename_deck_request(deck_id: int, name: str) -> bytes:
    msg = RenameDeckRequest()
    msg.deck_id = deck_id
    msg.name = name
    return msg.SerializeToString()


def encode_create_deck_request(name: str) -> bytes:
    msg = CreateDeckRequest()
    msg.name = name
    return msg.SerializeToString()


def _normalize_deck_node(proto_node: DeckNodeMessage) -> DeckNode:
    children = [_normalize_deck_node(child) for child in proto_node.children]
    return DeckNode(
        id=proto_node.deck_id,
        name=proto_node.name,
        level=proto_node.level,
        collapsed=proto_node.collapsed,
        review_count=proto_node.review_count,
        learn_count=proto_node.learn_count,
        new_count=proto_node.new_count,
        intraday_learning=proto_node.intraday_learning,
        interday_learning_uncapped=proto_node.interday_learning_uncapped,
        new_uncapped=proto_node.new_uncapped,
        review_uncapped=proto_node.review_uncapped,
        total_in_deck=proto_node.total_in_deck,
        total_including_children=proto_node.total_including_children,
        filtered=proto_node.filtered,
        children=children,
    )


__all__ = [
    "DeckNode",
    "encode_deck_list_info_request",
    "decode_deck_list_info_response",
    "DeckListInfoRequest",
    "DeckListInfoResponse",
    "encode_add_or_update_request",
    "AddOrUpdateRequest",
    "ModelSelection",
    "NoteId",
    "SearchRequest",
    "encode_search_request",
    "SearchResult",
    "SearchResponse",
    "decode_search_response",
    "RemoveDeckRequest",
    "encode_remove_deck_request",
    "RenameDeckRequest",
    "encode_rename_deck_request",
    "CreateDeckRequest",
    "encode_create_deck_request",
]
