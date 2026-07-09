"""Session memory store. In-memory dict keyed by session_id. Swap to Redis in production."""
from typing import Dict, Any
from copy import deepcopy

_SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_session(session_id: str) -> Dict[str, Any]:
    """Return session dict or create a new empty one."""
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {
            "session_id": session_id,
            "is_registered": False,
            "is_approved": False,
            "current_flow": "welcome",
            "current_step": "",
            "collected_data": {},
            "missing_fields_queue": [],
            "invalid_count": 0,
            "in_review_update_mode": False,
            "reply": "",
        }
    return _SESSIONS[session_id]


def save_session(session_id: str, state: Dict[str, Any]) -> None:
    """Persist updated state."""
    _SESSIONS[session_id] = deepcopy(state)


def clear_session(session_id: str) -> None:
    """Reset session (used after submit or by /reset)."""
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]
