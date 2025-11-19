from rememberit.proto import (
    DeckListInfoRequest,
    DeckListInfoResponse,
    decode_deck_list_info_response,
    encode_deck_list_info_request,
)


def test_encode_deck_list_info_request_sets_minutes() -> None:
    payload = encode_deck_list_info_request(600)
    req = DeckListInfoRequest.FromString(payload)
    assert req.minutes_west_of_utc == 600


def test_decode_deck_list_info_response_round_trip() -> None:
    resp = DeckListInfoResponse()
    top = resp.top_node  # type: ignore[attr-defined]
    top.deck_id = 1
    top.name = "Default"
    top.level = 0
    top.review_count = 2
    child = top.children.add()
    child.deck_id = 2
    child.name = "Sub"
    child.level = 1

    resp.current_deck_id = 1
    resp.collection_size_bytes = 10
    resp.media_size_bytes = 5

    decoded = decode_deck_list_info_response(resp.SerializeToString())

    assert decoded["current_deck_id"] == 1
    assert decoded["collection_size_bytes"] == 10
    assert decoded["media_size_bytes"] == 5
    assert decoded["top_node"].id == 1
    assert decoded["top_node"].children[0].id == 2
