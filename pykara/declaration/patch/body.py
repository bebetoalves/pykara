"""Patch declaration body models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PatchBody:
    """Pure data object that stores raw patch text."""

    text: str
