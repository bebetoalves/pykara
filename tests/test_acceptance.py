"""Acceptance tests for saved compatibility fixtures."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from pykara.data import Event
from tests.acceptance_support import build_expected_document, load_document

TESTS_DIR = Path(__file__).parent
ACCEPTANCE_DIR = TESTS_DIR / "fixtures" / "acceptance"


def _fixture_ids(path: Path) -> str:
    return path.stem


ACCEPTANCE_FIXTURES = tuple(
    sorted(
        (
            *ACCEPTANCE_DIR.glob("basic_*.ass"),
            *ACCEPTANCE_DIR.glob("advanced_*.ass"),
        )
    )
)


def _normalize_ass_time(value: int | float) -> int:
    """Match ASS centisecond quantization used by pysubs2 serialization."""

    return int(math.floor(value / 10.0 + 0.5) * 10)


def _normalize_event(event: Event) -> Event:
    return Event(
        text=event.text.rstrip(),
        effect=event.effect,
        style=event.style,
        layer=event.layer,
        start_time=_normalize_ass_time(event.start_time),
        end_time=_normalize_ass_time(event.end_time),
        comment=event.comment,
        actor=event.actor,
        margin_l=event.margin_l,
        margin_r=event.margin_r,
        margin_t=event.margin_t,
        margin_b=event.margin_b,
    )


@pytest.mark.parametrize("fixture_path", ACCEPTANCE_FIXTURES, ids=_fixture_ids)
def test_saved_acceptance_fixture_matches_regenerated_output(
    fixture_path: Path,
) -> None:
    expected_document = load_document(fixture_path)
    expected_fx_events = [
        event
        for event in expected_document.events
        if event.effect.lower() == "fx"
    ]
    assert expected_fx_events, "Acceptance fixture must include fx snapshots."

    regenerated_document = build_expected_document(fixture_path)

    assert regenerated_document.metadata == expected_document.metadata
    assert regenerated_document.styles == expected_document.styles
    assert [
        _normalize_event(event) for event in regenerated_document.events
    ] == [_normalize_event(event) for event in expected_document.events]
