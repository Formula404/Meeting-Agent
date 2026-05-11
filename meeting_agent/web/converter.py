from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def _lookup_userid(name: str, user_map: Dict[str, str]) -> str:
    """Lookup userid by Chinese name, return name as-is if not found."""
    return user_map.get(name, name)


def _lookup_dept_id(name: str, dept_map: Dict[str, str]) -> str:
    """Lookup department id by Chinese name, return name as-is if not found."""
    return dept_map.get(name, name)


def _parse_datetime_to_timestamp(dt_str: str) -> int:
    """Convert 'YYYY-MM-DD HH:mm' to Unix timestamp.
    Returns 0 if the string can't be parsed or is '未明确'.
    """
    cleaned = dt_str.strip()
    if not cleaned or cleaned in ("未明确", ""):
        return 0
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(cleaned, fmt).timestamp())
        except ValueError:
            continue
    return 0


def convert_result_for_push(
    raw: Dict[str, Any],
    user_map: Dict[str, str],
    dept_map: Dict[str, str],
) -> Dict[str, Any]:
    """Convert user-facing result (Chinese names, date strings) to
    push-ready format (userids, dept IDs, Unix timestamps).

    Args:
        raw:      Result dict with Chinese names and date strings.
        user_map: Mapping of Chinese name → WeCom userid.
        dept_map: Mapping of Chinese dept name → WeCom dept ID (as str).

    Returns:
        A new dict with all fields converted.
    """
    converted: Dict[str, Any] = dict(raw)

    # Convert push_user names → userids
    converted["push_user"] = [_lookup_userid(u, user_map) for u in raw.get("push_user", [])]

    # Convert push_dept names → dept IDs
    converted["push_dept"] = [_lookup_dept_id(d, dept_map) for d in raw.get("push_dept", [])]

    # Convert schedules
    schedules_out: List[Dict[str, Any]] = []
    for item in raw.get("schedules", []) or []:
        owners_raw = item.get("owner", [])
        if isinstance(owners_raw, str):
            owners_raw = [owners_raw]

        schedule: Dict[str, Any] = {
            "title": item.get("title", ""),
            "owner": [_lookup_userid(o, user_map) for o in owners_raw],
            "start_time": _parse_datetime_to_timestamp(item.get("start_time", "")),
            "end_time": _parse_datetime_to_timestamp(item.get("end_time", "")),
            "description": item.get("description", ""),
        }
        schedules_out.append(schedule)

    converted["schedules"] = schedules_out
    return converted
