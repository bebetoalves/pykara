"""CLI acceptance tests for saved compatibility fixtures."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pytest

from pykara.data import Event
from tests.acceptance_support import (
    build_expected_cli_document,
    build_expected_cli_json_document,
    load_document,
    load_json,
    run_cli,
)

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


@dataclass(frozen=True, slots=True)
class CliAcceptanceScenario:
    name: str
    extra_args: tuple[str, ...] = ()
    expect_json: bool = False


CLI_ACCEPTANCE_SCENARIOS = (
    CliAcceptanceScenario(name="ass", extra_args=("--seed", "1")),
    CliAcceptanceScenario(
        name="ass_json",
        extra_args=("--seed", "1", "--json", "{json_output}"),
        expect_json=True,
    ),
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


def _scenario_id(scenario: CliAcceptanceScenario) -> str:
    return scenario.name


@pytest.mark.parametrize("fixture_path", ACCEPTANCE_FIXTURES, ids=_fixture_ids)
@pytest.mark.parametrize(
    "scenario",
    CLI_ACCEPTANCE_SCENARIOS,
    ids=_scenario_id,
)
def test_saved_acceptance_fixture_matches_cli_output(
    fixture_path: Path,
    scenario: CliAcceptanceScenario,
    tmp_path: Path,
) -> None:
    expected_document = build_expected_cli_document(fixture_path)
    expected_fx_events = [
        event
        for event in expected_document.events
        if event.effect.lower() == "fx"
    ]
    assert expected_fx_events, "Acceptance fixture must include fx snapshots."

    output_path = tmp_path / f"{fixture_path.stem}_{scenario.name}.ass"
    json_path = tmp_path / f"{fixture_path.stem}_{scenario.name}.json"
    extra_args = tuple(
        str(json_path) if value == "{json_output}" else value
        for value in scenario.extra_args
    )

    result = run_cli(fixture_path, output_path, *extra_args)

    assert result.returncode == 0, result.stderr
    regenerated_document = load_document(output_path)

    assert regenerated_document.metadata == expected_document.metadata
    assert regenerated_document.styles == expected_document.styles
    assert [
        _normalize_event(event) for event in regenerated_document.events
    ] == [_normalize_event(event) for event in expected_document.events]

    if scenario.expect_json:
        assert load_json(json_path) == build_expected_cli_json_document(
            fixture_path
        )
