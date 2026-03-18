from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from grokipedia.errors import ParseError
from grokipedia.history import parse_edit_history_json
from grokipedia.models import EditHistoryPage


def _sample_payload() -> dict[str, object]:
    return {
        "editRequests": [
            {
                "id": "edit-1",
                "slug": "Sample_Page",
                "userId": "user-1",
                "status": "EDIT_REQUEST_STATUS_APPROVED",
                "type": "EDIT_REQUEST_TYPE_FIX_TYPO",
                "summary": "Fix typo in lead",
                "originalContent": "",
                "proposedContent": "the",
                "sectionTitle": "Overview",
                "createdAt": 1767558005,
                "updatedAt": 1767558074,
                "upvoteCount": 3,
                "downvoteCount": 1,
                "reviewReason": "",
            }
        ],
        "totalCount": 1,
        "hasMore": False,
    }


def test_edit_history_page_round_trips_json() -> None:
    history = EditHistoryPage.from_dict(_sample_payload())

    payload_from_json = json.loads(history.to_json())
    payload_from_dict = history.to_dict()

    assert payload_from_json == payload_from_dict
    assert EditHistoryPage.from_json(history.to_json()).to_dict() == payload_from_dict


def test_edit_history_epoch_fields_convert_to_utc_datetimes() -> None:
    history = EditHistoryPage.from_dict(_sample_payload())

    entry = history.edit_requests[0]
    assert entry.created_at_utc == datetime(2026, 1, 4, 20, 20, 5, tzinfo=timezone.utc)
    assert entry.updated_at_utc == datetime(2026, 1, 4, 20, 21, 14, tzinfo=timezone.utc)


def test_edit_history_optional_empty_strings_normalize_to_none() -> None:
    history = EditHistoryPage.from_dict(_sample_payload())

    entry = history.edit_requests[0]
    assert entry.original_content is None
    assert entry.review_reason is None
    assert entry.proposed_content == "the"


def test_edit_history_preserves_whitespace_in_edit_contents() -> None:
    payload = {
        "editRequests": [
            {
                "id": "edit-1",
                "slug": "Sample_Page",
                "userId": "user-1",
                "status": "EDIT_REQUEST_STATUS_APPROVED",
                "type": "EDIT_REQUEST_TYPE_FIX_TYPO",
                "summary": "Fix typo in lead",
                "originalContent": " teh",
                "proposedContent": " the\n",
                "sectionTitle": "Overview",
                "createdAt": 1767558005,
                "updatedAt": 1767558074,
                "upvoteCount": 3,
                "downvoteCount": 1,
                "reviewReason": "",
            }
        ],
        "totalCount": 1,
        "hasMore": False,
    }

    history = EditHistoryPage.from_dict(payload)

    entry = history.edit_requests[0]
    assert entry.original_content == " teh"
    assert entry.proposed_content == " the\n"


def test_parse_edit_history_json_rejects_non_object_payload() -> None:
    with pytest.raises(ParseError):
        parse_edit_history_json("[]")


def test_parse_edit_history_json_rejects_wrong_top_level_shape() -> None:
    with pytest.raises(ParseError):
        parse_edit_history_json(json.dumps({"editRequests": {}, "totalCount": 1}))


def test_edit_history_page_handles_empty_results() -> None:
    history = EditHistoryPage.from_dict(
        {"editRequests": [], "totalCount": 0, "hasMore": False}
    )

    assert history.edit_requests == []
    assert history.total_count == 0
    assert history.has_more is False
