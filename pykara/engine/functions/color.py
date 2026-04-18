"""Color helper functions exposed to the execution namespace."""

from __future__ import annotations

from typing import ClassVar

from pykara.support.interpolate import clamp, interpolate_color


def _clamp_byte(value: int) -> int:
    return int(clamp(value, 0, 255))


class AssColorFunction:
    """Return an ASS color string in ``&H00BBGGRR&`` format."""

    name: ClassVar[str] = "color.rgb_to_ass"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, r: int, g: int, b: int) -> str:
        del env
        red = _clamp_byte(r)
        green = _clamp_byte(g)
        blue = _clamp_byte(b)
        return f"&H00{blue:02X}{green:02X}{red:02X}&"


class AssAlphaFunction:
    """Return an ASS alpha string in ``&HAA&`` format."""

    name: ClassVar[str] = "color.alpha"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, a: int) -> str:
        del env
        alpha = _clamp_byte(a)
        return f"&H{alpha:02X}&"


class InterpolateColorFunction:
    """Return a color string interpolated between two ASS colors."""

    name: ClassVar[str] = "color.interpolate"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, t: float, c1: str, c2: str) -> str:
        del env
        return interpolate_color(t, c1, c2)
