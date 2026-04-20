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
        red: int,
        green: int,
        blue: int,
    ) -> str:
        del env
        red_component = _clamp_byte(red)
        green_component = _clamp_byte(green)
        blue_component = _clamp_byte(blue)
        return (
            f"&H00{blue_component:02X}{green_component:02X}{red_component:02X}&"
        )


class AssAlphaFunction:
    """Return an ASS alpha string in ``&HAA&`` format."""

    name: ClassVar[str] = "color.alpha"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, alpha: int) -> str:
        del env
        alpha_component = _clamp_byte(alpha)
        return f"&H{alpha_component:02X}&"


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
