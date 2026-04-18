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

    def __call__(
        self,
        env: object,
        red_value: int,
        green_value: int,
        blue_value: int,
    ) -> str:
        del env
        red = _clamp_byte(red_value)
        green = _clamp_byte(green_value)
        blue = _clamp_byte(blue_value)
        return f"&H00{blue:02X}{green:02X}{red:02X}&"


class AssAlphaFunction:
    """Return an ASS alpha string in ``&HAA&`` format."""

    name: ClassVar[str] = "color.alpha"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, alpha_value: int) -> str:
        del env
        alpha = _clamp_byte(alpha_value)
        return f"&H{alpha:02X}&"


class InterpolateColorFunction:
    """Return a color string interpolated between two ASS colors."""

    name: ClassVar[str] = "color.interpolate"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        progress: float,
        start_color: str,
        end_color: str,
    ) -> str:
        del env
        return interpolate_color(progress, start_color, end_color)
