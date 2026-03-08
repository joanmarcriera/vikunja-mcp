"""Task state model encoded in `status:*` labels."""

from __future__ import annotations

ALLOWED_STATES = {
    "inbox",
    "ready",
    "claimed",
    "in_progress",
    "blocked",
    "review",
    "done",
    "cancelled",
}

TRANSITIONS = {
    "inbox": {"ready", "cancelled"},
    "ready": {"claimed", "blocked", "cancelled"},
    "claimed": {"in_progress", "ready", "blocked", "cancelled"},
    "in_progress": {"review", "blocked", "ready", "cancelled"},
    "blocked": {"ready", "cancelled"},
    "review": {"done", "ready", "in_progress", "cancelled"},
    "done": set(),
    "cancelled": set(),
}


def _label_name(label: str | dict) -> str:
    if isinstance(label, str):
        return label
    if isinstance(label, dict):
        for key in ("title", "name", "label"):
            value = label.get(key)
            if isinstance(value, str):
                return value
    return ""


def extract_state(labels: list[str] | list[dict]) -> str | None:
    states = []
    for item in labels:
        name = _label_name(item)
        if name.startswith("status:"):
            candidate = name.split(":", 1)[1].strip()
            if candidate in ALLOWED_STATES:
                states.append(candidate)
    if not states:
        return None
    if len(states) > 1:
        raise ValueError(f"multiple status labels found: {states}")
    return states[0]


def replace_state(labels: list[str] | list[dict], new_state: str) -> list[str]:
    if new_state not in ALLOWED_STATES:
        raise ValueError(f"invalid state: {new_state}")
    kept: list[str] = []
    for item in labels:
        name = _label_name(item)
        if not name.startswith("status:"):
            kept.append(name)
    kept.append(f"status:{new_state}")
    # Preserve order while dropping duplicates.
    return list(dict.fromkeys(kept))


def validate_transition(old_state: str, new_state: str, *, force: bool = False) -> None:
    if old_state not in ALLOWED_STATES:
        raise ValueError(f"unknown current state: {old_state}")
    if new_state not in ALLOWED_STATES:
        raise ValueError(f"unknown target state: {new_state}")
    if force:
        return
    if new_state not in TRANSITIONS[old_state]:
        raise ValueError(f"invalid transition: {old_state} -> {new_state}")
