from __future__ import annotations

import json

from .errors import ParseError
from .models import EditHistoryPage


def parse_edit_history_json(payload: str) -> EditHistoryPage:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Unable to parse edit history JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ParseError("Edit history payload must decode to an object")

    try:
        return EditHistoryPage.from_dict(data)
    except ValueError as exc:
        raise ParseError(f"Invalid edit history payload: {exc}") from exc
