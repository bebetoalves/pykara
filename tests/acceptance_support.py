"""Shared helpers for acceptance fixture regeneration and validation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pykara.adapters import SubtitleDocument
from pykara.adapters.input.sub_station_alpha import SubStationAlphaReader
from pykara.adapters.output.json_adapter import JsonWriter
from pykara.data import Event
from pykara.declaration.code import CODE_MODIFIER_REGISTRY
from pykara.declaration.mixin import MIXIN_MODIFIER_REGISTRY
from pykara.declaration.template import TEMPLATE_MODIFIER_REGISTRY
from pykara.engine import Engine
from pykara.parsing import DeclarationParser
from pykara.processing import FontMetricsProvider, LinePreprocessor

TESTS_DIR = Path(__file__).parent
ROOT_DIR = TESTS_DIR.parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
FONT_FIXTURE_DIR = FIXTURES_DIR / "fonts"
CLI_BIN = ROOT_DIR / ".venv" / "bin" / "pykara"


def _copy_event(
    event: Event,
    *,
    comment: bool | None = None,
) -> Event:
    """Return a shallow event clone with an optional comment override."""

    return Event(
        text=event.text,
        effect=event.effect,
        style=event.style,
        layer=event.layer,
        start_time=event.start_time,
        end_time=event.end_time,
        comment=event.comment if comment is None else comment,
        actor=event.actor,
        margin_l=event.margin_l,
        margin_r=event.margin_r,
        margin_t=event.margin_t,
        margin_b=event.margin_b,
    )


def load_document(path: Path) -> SubtitleDocument:
    """Read one ASS fixture from disk."""

    return SubStationAlphaReader().read(path)


def load_json(path: Path) -> dict[str, object]:
    """Read one JSON fixture from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def strip_fx_events(document: SubtitleDocument) -> SubtitleDocument:
    """Return a copy of the document without generated ``fx`` events."""

    return SubtitleDocument(
        metadata=document.metadata,
        styles=document.styles,
        events=[
            event for event in document.events if event.effect.lower() != "fx"
        ],
    )


def _activate_karaoke_inputs(document: SubtitleDocument) -> SubtitleDocument:
    """Clone the document with karaoke source lines enabled for execution."""

    return SubtitleDocument(
        metadata=document.metadata,
        styles=document.styles,
        events=[
            _copy_event(
                event,
                comment=(
                    False if event.effect.lower() == "karaoke" else None
                ),
            )
            for event in document.events
        ],
    )


def regenerate_fx_events(path: Path) -> tuple[SubtitleDocument, list[Event]]:
    """Regenerate fx events from one saved acceptance fixture."""

    document = strip_fx_events(load_document(path))
    executable_document = _activate_karaoke_inputs(document)
    declarations = DeclarationParser(
        template_mod_registry=TEMPLATE_MODIFIER_REGISTRY,
        mixin_mod_registry=MIXIN_MODIFIER_REGISTRY,
        code_mod_registry=CODE_MODIFIER_REGISTRY,
    ).parse(executable_document.events)
    preprocessor = LinePreprocessor(extents=FontMetricsProvider())
    fx_events = Engine(preprocessor, seed=1).apply(
        executable_document.events,
        declarations,
        executable_document.metadata,
        executable_document.styles,
    )
    return document, fx_events


def build_expected_document(path: Path) -> SubtitleDocument:
    """Return the merged document expected for one acceptance fixture."""

    document, fx_events = regenerate_fx_events(path)
    return SubtitleDocument(
        metadata=document.metadata,
        styles=document.styles,
        events=[*document.events, *fx_events],
    )


def build_expected_cli_document(path: Path) -> SubtitleDocument:
    """Return the document shape written by the CLI for one fixture."""

    document = build_expected_document(path)
    return SubtitleDocument(
        metadata=document.metadata,
        styles=document.styles,
        events=[
            _copy_event(
                event,
                comment=(
                    True if event.effect.lower() == "karaoke" else None
                ),
            )
            for event in document.events
        ],
    )


def build_expected_cli_json_document(path: Path) -> dict[str, object]:
    """Return the JSON payload expected from the CLI for one fixture."""

    return JsonWriter().to_dict(build_expected_cli_document(path))


def run_cli(
    input_path: Path,
    output_path: Path,
    *extra_args: str,
    use_font_dir: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Execute the real CLI in a subprocess."""

    command = [
        str(CLI_BIN),
        str(input_path),
        str(output_path),
        *extra_args,
    ]
    if use_font_dir:
        command.extend(["--font-dir", str(FONT_FIXTURE_DIR)])

    return subprocess.run(  # noqa: S603 - test helper executes repo-owned fixture paths
        command,
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )
