from __future__ import annotations

import pytest

from vikunja_mcp.state_machine import (
    extract_state,
    replace_state,
    validate_transition,
)


def test_extract_state_none_when_missing() -> None:
    assert extract_state(["agent:coder", "priority:high"]) is None


def test_extract_state_from_dict_labels() -> None:
    assert extract_state([{"title": "status:ready"}, {"title": "agent:coder"}]) == "ready"


def test_extract_state_raises_when_multiple_status() -> None:
    with pytest.raises(ValueError):
        extract_state(["status:ready", "status:blocked"])


def test_replace_state_keeps_other_labels() -> None:
    labels = replace_state(["agent:coder", "status:ready", "repo:foo"], "claimed")
    assert "status:claimed" in labels
    assert "status:ready" not in labels
    assert "agent:coder" in labels


def test_validate_transition_rejects_invalid_edge() -> None:
    with pytest.raises(ValueError):
        validate_transition("ready", "done")


def test_validate_transition_accepts_allowed_edge() -> None:
    validate_transition("ready", "claimed")
