"""Shared helpers for acceptance fixture regeneration and validation."""

from __future__ import annotations

from pathlib import Path

from pykara.adapters import SubtitleDocument
from pykara.adapters.input.sub_station_alpha import SubStationAlphaReader
from pykara.data import Event
from pykara.declaration.code import CODE_MODIFIER_REGISTRY
from pykara.declaration.mixin import MIXIN_MODIFIER_REGISTRY
from pykara.declaration.template import TEMPLATE_MODIFIER_REGISTRY
from pykara.engine import Engine
from pykara.parsing import DeclarationParser
from pykara.processing import FontMetricsProvider, LinePreprocessor


def load_document(path: Path) -> SubtitleDocument:
    """Read one ASS fixture from disk."""

    return SubStationAlphaReader().read(path)


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
            Event(
                text=event.text,
                effect=event.effect,
                style=event.style,
                layer=event.layer,
                start_time=event.start_time,
                end_time=event.end_time,
                comment=(
                    False
                    if event.effect.lower() == "karaoke"
                    else event.comment
                ),
                actor=event.actor,
                margin_l=event.margin_l,
                margin_r=event.margin_r,
                margin_t=event.margin_t,
                margin_b=event.margin_b,
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
