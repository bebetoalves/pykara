"""Unit tests for template text rendering."""

from __future__ import annotations

import builtins
import random
from types import CodeType

import pytest

from pykara.data import Event, Highlight, Karaoke, Metadata, Style, Syllable
from pykara.engine.variable_context import Environment
from pykara.errors import (
    BoundMethodInExpressionError,
    TemplateCodeError,
    TemplateRuntimeError,
    UnknownVariableError,
)
from pykara.processing.text_renderer import TextRenderer


def make_style() -> Style:
    return Style(
        name="Default",
        fontname="Arial",
        fontsize=24.0,
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


def make_env() -> Environment:
    env = Environment(
        styles={"Default": make_style()},
        declaration="template",
        rng=random.Random(1),  # noqa: S311
    )
    env.source_line = Event(
        text="go",
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=100,
        end_time=300,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )
    env.vars.set_line(
        index=0,
        start_time=100,
        end_time=300,
        width=50.0,
        height=20.0,
        left=10.0,
        center=35.0,
        right=60.0,
        top=70.0,
        middle=80.0,
        bottom=90.0,
        x=35.0,
        y=90.0,
        syllable_count=2,
        word_count=1,
    )
    return env


class TestTextRenderer:
    def test_renders_variables_and_expressions(self) -> None:
        renderer = TextRenderer()

        rendered = renderer.render(
            r"pos($line_center,$line_middle)!line.center + 2!",
            make_env(),
        )

        assert rendered == r"pos(35,80)37"

    def test_exposes_style_object_in_expressions(self) -> None:
        renderer = TextRenderer()
        env = make_env()

        rendered = renderer.render(
            "!style.primary_color!-!style.shadow_color!-!style.outline!",
            env,
        )

        assert rendered == "&H00FFFFFF-&H00000000-2.0"

    def test_exposes_source_and_text_views_in_expressions(self) -> None:
        renderer = TextRenderer()
        env = make_env()
        env.karaoke = Karaoke(syllables=[], text="go", trimmed_text="go")

        rendered = renderer.render(
            "!line.raw_text!-!line.text!-!line.trimmed_text!",
            env,
        )

        assert rendered == "go-go-go"

    def test_exposes_seeded_random_object_in_expressions(self) -> None:
        renderer = TextRenderer()

        rendered = renderer.render(
            "!random.randint(1, 10)!-!random.randint(1, 10)!",
            make_env(),
        )

        assert rendered == "3-10"

    def test_exposes_metadata_object_in_expressions(self) -> None:
        renderer = TextRenderer()
        env = make_env()
        env.metadata = Metadata(res_x=1920, res_y=1080)

        rendered = renderer.render("!metadata.res_x!x!metadata.res_y!", env)

        assert rendered == "1920x1080"

    def test_caches_compiled_expressions(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        renderer = TextRenderer()
        compile_calls = 0
        original_compile = builtins.compile

        def counting_compile(
            source: str,
            filename: str,
            mode: str,
            flags: int = 0,
            dont_inherit: bool = False,
            optimize: int = -1,
            _feature_version: int = -1,
        ) -> CodeType:
            nonlocal compile_calls
            compile_calls += 1
            return original_compile(
                source,
                filename,
                mode,
                flags=flags,
                dont_inherit=dont_inherit,
                optimize=optimize,
                _feature_version=_feature_version,
            )

        monkeypatch.setattr(builtins, "compile", counting_compile)

        env = make_env()
        assert renderer.render("!line.center + 2!", env) == "37"
        assert renderer.render("!line.center + 2!", env) == "37"
        assert compile_calls == 1

    def test_exposes_line_syllables_in_expressions(self) -> None:
        renderer = TextRenderer()
        env = make_env()
        env.karaoke = Karaoke(
            syllables=[
                Syllable(
                    index=0,
                    raw_text="go",
                    text="go",
                    trimmed_text="go",
                    prespace="",
                    postspace="",
                    start_time=100,
                    end_time=300,
                    duration=200,
                    kdur=20.0,
                    tag="\\k20",
                    inline_fx="",
                    highlights=[Highlight(100, 300, 200)],
                    center=35.5,
                ),
                Syllable(
                    index=1,
                    raw_text="al",
                    text="al",
                    trimmed_text="al",
                    prespace="",
                    postspace="",
                    start_time=300,
                    end_time=500,
                    duration=200,
                    kdur=20.0,
                    tag="\\k20",
                    inline_fx="",
                    highlights=[Highlight(300, 500, 200)],
                    center=55.5,
                ),
            ],
            text="goal",
            trimmed_text="goal",
        )

        rendered = renderer.render(
            "!line.syls[0].start_time!-!line.syls[1].center!",
            env,
        )

        assert rendered == "100-55.5"

    def test_exposes_syllable_tag_family_in_expressions(self) -> None:
        renderer = TextRenderer()
        env = make_env()
        syllable = Syllable(
            index=0,
            raw_text="go",
            text="go",
            trimmed_text="go",
            prespace="",
            postspace="",
            start_time=100,
            end_time=300,
            duration=200,
            kdur=20.0,
            tag="\\kf20",
            inline_fx="",
            highlights=[Highlight(100, 300, 200)],
        )
        env.vars.set_syl(syllable)
        env.syl = syllable

        rendered = renderer.render("!syl.tag!", env)

        assert rendered == "\\kf"

    def test_exposes_syllable_inline_fx_in_expressions(self) -> None:
        renderer = TextRenderer()
        env = make_env()
        syllable = Syllable(
            index=0,
            raw_text="go",
            text="go",
            trimmed_text="go",
            prespace="",
            postspace="",
            start_time=100,
            end_time=300,
            duration=200,
            kdur=20.0,
            tag="\\k20",
            inline_fx="flash",
            highlights=[Highlight(100, 300, 200)],
        )
        env.vars.set_syl(syllable)
        env.syl = syllable

        rendered = renderer.render("!syl.inline_fx!", env)

        assert rendered == "flash"

    def test_raises_on_unknown_variable(self) -> None:
        renderer = TextRenderer()

        with pytest.raises(UnknownVariableError):
            renderer.render("$missing", make_env())

    def test_raises_template_code_error_on_invalid_expression(self) -> None:
        renderer = TextRenderer()

        with pytest.raises(TemplateCodeError):
            renderer.render("!for!", make_env())

    def test_raises_template_runtime_error_on_expression_failure(self) -> None:
        renderer = TextRenderer()

        with pytest.raises(TemplateRuntimeError):
            renderer.render("!1 / 0!", make_env())

    def test_raises_on_callable_expression_result(self) -> None:
        renderer = TextRenderer()

        with pytest.raises(BoundMethodInExpressionError):
            renderer.render("!layer.set!", make_env())

    def test_renders_none_expression_result_as_empty_string(self) -> None:
        renderer = TextRenderer()

        assert renderer.render("a!None!b", make_env()) == "ab"
