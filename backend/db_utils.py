from collections.abc import Sequence
from typing import Any

from sqlalchemy.engine import RowMapping


def row_to_dict(row: RowMapping | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: Sequence[RowMapping]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
