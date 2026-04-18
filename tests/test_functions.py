"""Unit tests for engine namespace functions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import ClassVar, cast

import pytest

from pykara.data import Style
from pykara.declaration import Scope
from pykara.engine.functions import (
    FUNCTION_REGISTRY,
    AssAlphaFunction,
    AssColorFunction,
    FunctionRegistry,
    GetFunction,
    InterpolateColorFunction,
    PolarFunction,
    RelayerFunction,
    RetimeFunction,
    RoundCoordFunction,
    SetFunction,
    ShapeCenterposFunction,
    ShapeDisplaceFunction,
    ShapeRotateFunction,
    ShapeSliderFunction,
)
from pykara.errors import EngineError


@dataclass(slots=True)
class DummyTimedLine:
    start_time: int
    end_time: int


@dataclass(slots=True)
class DummySyllable:
    start_time: int
    end_time: int
    duration: int
    index: int = 0
    center: float = 0.0
    x: float = 0.0


@dataclass(slots=True)
class DummyGeneratedLine:
    start_time: int = 0
    end_time: int = 0
    duration: int = 0
    layer: int = 0
    style: str = "Default"
    styleref: Style | None = None


@dataclass(slots=True)
class DummyEnvironment:
    source_line: DummyTimedLine = field(
        default_factory=lambda: DummyTimedLine(start_time=1000, end_time=5000)
    )
    line: DummyGeneratedLine = field(default_factory=DummyGeneratedLine)
    syl: DummySyllable | None = field(
        default_factory=lambda: DummySyllable(
            start_time=500,
            end_time=900,
            duration=400,
        )
    )
    word: DummySyllable | None = None
    char: DummySyllable | None = None
    char_index: int | None = None
    line_char_count: int | None = None
    active_template_scope: Scope | None = Scope.SYL
    retime_used: bool = False
    retime_line_words: tuple[DummySyllable, ...] = ()
    retime_line_syls: tuple[DummySyllable, ...] = field(
        default_factory=lambda: (
            DummySyllable(
                start_time=500,
                end_time=900,
                duration=400,
                index=0,
                center=10.0,
                x=10.0,
            ),
            DummySyllable(
                start_time=1000,
                end_time=1300,
                duration=300,
                index=1,
                center=30.0,
                x=30.0,
            ),
        )
    )
    retime_line_chars: tuple[DummySyllable, ...] = ()
    retime_syl_chars: tuple[DummySyllable, ...] = ()
    styles: dict[str, Style] = field(default_factory=lambda: _empty_styles())
    store: dict[str, object] = field(default_factory=lambda: _empty_store())


def _empty_styles() -> dict[str, Style]:
    return {}


def _empty_store() -> dict[str, object]:
    return {}


def make_style(name: str = "Default") -> Style:
    return Style(
        name=name,
        fontname="Arial",
        fontsize=36.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H000000FF",
        outline_colour="&H00000000",
        back_colour="&H00000000",
        bold=False,
        italic=False,
        underline=False,
        strike_out=False,
        scale_x=100.0,
        scale_y=100.0,
        spacing=0.0,
        angle=0.0,
        border_style=1,
        outline=2.0,
        shadow=0.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=10,
        margin_b=10,
        encoding=1,
    )


class TestRetimeFunction:
    @pytest.mark.parametrize(
        ("target", "start_offset", "end_offset", "expected"),
        [
            ("syl", 10, 20, (1510, 1920)),
            ("presyl", 10, 20, (1510, 1520)),
            ("postsyl", 10, 20, (1910, 1920)),
            ("line", 10, 20, (1010, 5020)),
            ("preline", 10, 20, (1010, 1020)),
            ("postline", 10, 20, (5010, 5020)),
            ("start2syl", 10, 20, (1010, 1520)),
            ("syl2end", 10, 20, (1910, 5020)),
        ],
    )
    def test_applies_target_and_updates_duration(
        self,
        target: str,
        start_offset: int,
        end_offset: int,
        expected: tuple[int, int],
    ) -> None:
        env = DummyEnvironment()

        retime = RetimeFunction().build_bound(env)
        result = getattr(retime, target)(start_offset, end_offset)

        assert result == ""
        assert (env.line.start_time, env.line.end_time) == expected
        assert env.line.duration == expected[1] - expected[0]

    def test_direct_call_is_not_supported(self) -> None:
        with pytest.raises(EngineError):
            RetimeFunction()(DummyEnvironment(), "syl")

    def test_rejects_second_retime_call_in_same_evaluation(self) -> None:
        env = DummyEnvironment()
        retime = RetimeFunction().build_bound(env)

        retime.line()

        with pytest.raises(EngineError):
            retime.syl()

    def test_rejects_syllable_target_in_line_scope(self) -> None:
        env = DummyEnvironment(active_template_scope=Scope.LINE)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError):
            retime.syl()

    def test_applies_line_preset_to_syllable_collection(self) -> None:
        env = DummyEnvironment(
            syl=DummySyllable(
                start_time=500,
                end_time=900,
                duration=400,
                index=1,
                center=30.0,
                x=30.0,
            )
        )
        retime = RetimeFunction().build_bound(env)

        retime.line.ltr(-300, 200)

        assert (env.line.start_time, env.line.end_time) == (1000, 5200)

    def test_rejects_degenerate_preset_collection(self) -> None:
        env = DummyEnvironment(retime_line_syls=(DummySyllable(0, 100, 100),))
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError):
            retime.line.ltr(-300, 0)


class TestRelayerFunction:
    def test_sets_layer(self) -> None:
        env = DummyEnvironment()

        result = RelayerFunction()(env, 7)

        assert result == ""
        assert env.line.layer == 7


class TestStoreFunctions:
    def test_get_returns_default(self) -> None:
        env = DummyEnvironment()

        result = GetFunction()(env, "missing", "fallback")

        assert result == "fallback"

    def test_set_stores_and_returns_value(self) -> None:
        env = DummyEnvironment()

        result = SetFunction()(env, "color", "blue")

        assert result == "blue"
        assert env.store["color"] == "blue"


class TestColorFunctions:
    def test_ass_color_formats_ass_string(self) -> None:
        result = AssColorFunction()(object(), 255, 128, 0)

        assert result == "&H000080FF&"

    def test_ass_alpha_formats_ass_string(self) -> None:
        result = AssAlphaFunction()(object(), 255)

        assert result == "&HFF&"

    def test_interpolate_color_supports_style_and_override_formats(
        self,
    ) -> None:
        result = InterpolateColorFunction()(
            object(),
            0.5,
            "&H00000000",
            "&HFFFFFF&",
        )

        assert result == "&H00808080&"


class TestGeometryFunctions:
    def test_polar_uses_screen_space_y_axis(self) -> None:
        polar = PolarFunction()

        assert polar(object(), 0, 30, "x") == 30
        assert polar(object(), 90, 30, "y") == -30
        assert polar(object(), 180, 30) == (-30, -0.0)

    def test_round_coord_matches_ass_coordinate_rounding(self) -> None:
        round_coord = RoundCoordFunction()

        assert round_coord(object(), 3.49) == 3
        assert round_coord(object(), 3.5) == 4

    def test_shape_rotate_centerpos_and_displace(self) -> None:
        shape = "m 0 0 l 10 0 l 10 20"

        rotated = ShapeRotateFunction()(object(), shape, 90)
        centered = ShapeCenterposFunction()(object(), rotated)
        displaced = ShapeDisplaceFunction()(object(), centered, 50, 60)

        assert rotated == "m 0 0 l 0 -10 l 20 -10"
        assert centered == "m -10 5 l -10 -5 l 10 -5"
        assert displaced == "m 40 65 l 40 55 l 60 55"

    def test_shape_slider_builds_centered_split_clip(self) -> None:
        result = ShapeSliderFunction()(object(), 20, 0, 50, 60)

        assert result == "m 40 60 l 60 60 l 60 50 l 40 50 m 40 70 l 60 70"


class CodeOnlyFunction:
    name: ClassVar[str] = "code_only"
    aliases: ClassVar[tuple[str, ...]] = ("code_alias",)
    applicable_to: ClassVar[frozenset[str]] = frozenset({"code"})

    def __call__(self, env: object, value: str) -> str:
        del env
        return value.upper()


class TestFunctionRegistry:
    def test_build_namespace_binds_environment(self) -> None:
        env = DummyEnvironment()
        registry = FunctionRegistry()
        registry.register(RelayerFunction())

        namespace = registry.build_namespace(env, "template")
        relayer = cast(Callable[[int], object], namespace["relayer"])
        assert isinstance(relayer, Callable)
        result = relayer(4)

        assert result == ""
        assert env.line.layer == 4

    def test_filters_by_declaration(self) -> None:
        registry = FunctionRegistry()
        registry.register(CodeOnlyFunction())

        template_namespace = registry.build_namespace(object(), "template")
        code_namespace = registry.build_namespace(object(), "code")

        assert "code_only" not in template_namespace
        assert "code_alias" not in template_namespace
        code_only = code_namespace["code_only"]
        code_alias = code_namespace["code_alias"]
        assert isinstance(code_only, Callable)
        assert isinstance(code_alias, Callable)
        assert code_only("hello") == "HELLO"
        assert code_alias("world") == "WORLD"

    def test_build_namespace_groups_dotted_functions(self) -> None:
        registry = FunctionRegistry()
        registry.register(PolarFunction())

        namespace = registry.build_namespace(object(), "template")

        assert "math.polar" not in namespace
        assert isinstance(namespace["math"], SimpleNamespace)
        assert namespace["math"].polar(0, 30, "x") == 30


class TestDefaultRegistry:
    def test_default_registry_exposes_core_functions(self) -> None:
        env = DummyEnvironment()
        namespace = FUNCTION_REGISTRY.build_namespace(env, "template")

        assert "retime" in namespace
        assert "relayer" in namespace
        assert "get" in namespace
        assert "set" in namespace
        assert isinstance(namespace["color"], SimpleNamespace)
        assert isinstance(namespace["math"], SimpleNamespace)
        assert isinstance(namespace["coord"], SimpleNamespace)
        assert isinstance(namespace["shape"], SimpleNamespace)
        assert namespace["color"].ass(255, 128, 0) == "&H000080FF&"
        assert namespace["color"].alpha(255) == "&HFF&"
        assert (
            namespace["color"].interpolate(
                0.5,
                "&H00000000",
                "&HFFFFFF&",
            )
            == "&H00808080&"
        )
        assert namespace["math"].polar(0, 30, "x") == 30
        assert namespace["coord"].round(3.5) == 4
        assert namespace["shape"].rotate("m 0 0 l 10 0", 90) == (
            "m 0 0 l 0 -10"
        )
        assert namespace["shape"].centerpos("m 0 0 l 10 0") == ("m -5 0 l 5 0")
        assert namespace["shape"].displace("m 0 0", 1, 2) == "m 1 2"
        assert namespace["shape"].slider(20, 0, 50, 60) == (
            "m 40 60 l 60 60 l 60 50 l 40 50 m 40 70 l 60 70"
        )
