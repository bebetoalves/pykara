"""Unit and integration tests for engine execution."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import builtins
import random
from dataclasses import dataclass
from types import CodeType

import pytest

from pykara.data import Event, Metadata, Style
from pykara.declaration import Scope
from pykara.declaration.code import CodeBody
from pykara.declaration.template import (
    LoopDescriptor,
    TemplateBody,
    TemplateModifiers,
)
from pykara.engine.engine import Engine, _CodeRunner
from pykara.engine.variable_context import Environment
from pykara.errors import (
    BoundMethodInExpressionError,
    TemplateCodeError,
    TemplateRuntimeError,
    UnknownVariableError,
)
from pykara.parsing import (
    CodeDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.processing.font_metrics import TextMeasurement
from pykara.processing.line_preprocessor import LinePreprocessor


@dataclass(slots=True)
class FakeExtentsProvider:
    widths: dict[str, float]

    def measure(self, style: Style, text: str) -> TextMeasurement:
        del style
        return TextMeasurement(
            width=self.widths.get(text, float(len(text) * 10)),
            height=20.0,
            descent=4.0,
            extlead=0.0,
        )


@dataclass(slots=True)
class CountingExtentsProvider:
    widths: dict[str, float]
    calls: int = 0

    def measure(self, style: Style, text: str) -> TextMeasurement:
        del style
        self.calls += 1
        return TextMeasurement(
            width=self.widths.get(text, float(len(text) * 10)),
            height=20.0,
            descent=4.0,
            extlead=0.0,
        )


def make_style() -> Style:
    return Style(
        name="Default",
        fontname="Arial",
        fontsize=40.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H0000FFFF",
        outline_colour="&H00000000",
        back_colour="&H64000000",
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
        shadow=1.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=10,
        margin_b=10,
        encoding=1,
    )


def make_event() -> Event:
    return Event(
        text=r"{\k20}go{\k30}al",
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=1000,
        end_time=1500,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_single_syllable_event() -> Event:
    return Event(
        text=r"{\k50}go",
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=1000,
        end_time=1500,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_env() -> Environment:
    return Environment(
        styles={"Default": make_style()},
        declaration="code",
        rng=random.Random(1),  # noqa: S311
    )


class TestCodeRunnerCaching:
    def test_caches_compiled_code(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        runner = _CodeRunner()
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
        runner.run("value = 1", env)
        runner.run("value = 1", env)

        assert env.user_namespace["value"] == 1
        assert compile_calls == 1

    def test_caches_expanded_char_syllables_per_environment(self) -> None:
        extents = CountingExtentsProvider({"g": 10.0, "o": 10.0})
        preprocessor = LinePreprocessor(extents)
        engine = Engine(preprocessor, rng_seed=1)
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )
        syllable = preprocessor.preprocess(
            make_single_syllable_event(),
            engine._karaoke_parser.parse(make_single_syllable_event()),
            Metadata(res_x=1920, res_y=1080),
            make_style(),
        ).syllables[0]
        calls_before = extents.calls

        first = engine._iter_char_syllables(env, syllable)
        second = engine._iter_char_syllables(env, syllable)

        assert first == second
        assert extents.calls - calls_before == 2


def build_engine() -> Engine:
    extents = FakeExtentsProvider(
        {
            "goal": 40.0,
            "": 0.0,
            "go": 20.0,
            "al": 20.0,
            "g": 10.0,
            "o": 10.0,
            "a": 10.0,
            "l": 10.0,
        }
    )
    return Engine(LinePreprocessor(extents), rng_seed=1)


class TestCodeRunner:
    def test_executes_valid_code_and_persists_namespace(self) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run("helper = 7", env)

        assert env.user_namespace["helper"] == 7

    def test_allows_reassigning_existing_user_namespace_values(self) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run("value = 1", env)
        runner.run("value = value + 1", env)

        assert env.user_namespace["value"] == 2

    def test_raises_template_code_error_on_syntax_failure(self) -> None:
        runner = _CodeRunner()

        with pytest.raises(TemplateCodeError):
            runner.run("def broken(: pass", make_env())

    def test_raises_template_runtime_error_on_execution_failure(self) -> None:
        runner = _CodeRunner()

        with pytest.raises(TemplateRuntimeError):
            runner.run("1 / 0", make_env())


class TestEngineIntegration:
    def test_applies_code_setup_line_syl_and_char_templates(self) -> None:
        engine = build_engine()
        event = make_event()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody("prefix = 'P:'"),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!prefix!L$line_i-"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ],
            syl=[
                CodeDeclaration(
                    body=CodeBody("seen = set('last', syl.i)"),
                    scope=Scope.SYL,
                ),
                TemplateDeclaration(
                    body=TemplateBody("S$syl_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                ),
            ],
            char=[
                TemplateDeclaration(
                    body=TemplateBody("C$char_n-$char_x:"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(no_text=False),
                )
            ],
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "P:L0-",
            "S0:go",
            "C2-945:g",
            "C2-955:o",
            "S1:al",
            "C2-965:a",
            "C2-975:l",
        ]
        assert all(result.effect == "fx" for result in results)

    def test_code_setup_does_not_expose_store_functions(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody("set('main', 1)"),
                    scope=Scope.SETUP,
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_applies_word_templates_grouped_by_spaces(self) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k20}go{\k30} al{\k10}!",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1600,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            word=[
                TemplateDeclaration(
                    body=TemplateBody(
                        "W$word_i/$word_n:$word_left-$word_right:"
                    ),
                    scope=Scope.WORD,
                    modifiers=TemplateModifiers(),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "W0/2:930-950:go",
            "W1/2:960-990: al!",
        ]

    def test_syllable_scope_can_access_current_word(self) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k20}go{\k30} al{\k10}!",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1600,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("$word_i-$syl_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "0-0:go",
            "1-1: al",
            "1-2:!",
        ]

    def test_word_scope_cannot_access_syllable_object(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            word=[
                CodeDeclaration(
                    body=CodeBody("bad = syl.i"),
                    scope=Scope.WORD,
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_exposes_metadata_object_in_template_expressions(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!metadata.res_x!x!metadata.res_y!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["1920x1080"]

    def test_exposes_syllable_tag_family_in_template_expressions(
        self,
    ) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k20}go{\kf30}al",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1500,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!syl.tag!"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["\\k", "\\kf"]

    def test_supports_when_unless_and_loop(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("W$loop_i/$loop_n"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        when="syl.i == 0",
                        loops=(LoopDescriptor(name="i", iterations=2),),
                    ),
                ),
                TemplateDeclaration(
                    body=TemplateBody("U"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(unless="syl.i == 0"),
                ),
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "W0/2go",
            "W1/2go",
        ]

    def test_supports_loop_expression_counts(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("L$loop_j_i/$loop_j_n:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        loops=(
                            LoopDescriptor(
                                name="j",
                                iterations="math.floor($syl_width / 10)",
                                explicit_name="j",
                            ),
                        ),
                    ),
                )
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "L0/2:go",
            "L1/2:go",
        ]

    def test_declarations_apply_only_to_matching_style_by_default(
        self,
    ) -> None:
        engine = build_engine()
        event = make_single_syllable_event()
        declarations = ParsedDeclarations(
            syl=[
                CodeDeclaration(
                    body=CodeBody("shared = 'A'"),
                    scope=Scope.SYL,
                    style="",
                ),
                TemplateDeclaration(
                    body=TemplateBody("M!shared!:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                    style="Default",
                ),
                TemplateDeclaration(
                    body=TemplateBody("S"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                    style="Other",
                ),
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["MA:go"]

    def test_reassigns_line_code_variables_for_each_line(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody("value = line.i"),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!value!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        results = engine.apply(
            [make_event(), make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["0", "1"]

    def test_line_code_uses_current_source_line_timing(self) -> None:
        engine = build_engine()
        second_event = Event(
            text=r"{\k50}go",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=2000,
            end_time=2600,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody(
                        "gap = line.start - get('prev_end',"
                        " line.start - 1000);"
                        " set('prev_end', line.end)"
                    ),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!gap!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        results = engine.apply(
            [make_event(), second_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["1000", "500"]

    def test_line_code_functions_capture_current_line_namespace(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody(
                        "label = 'ready'\n"
                        "def describe(): return f'{line.start}:{label}'"
                    ),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!describe()!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        results = engine.apply(
            [make_event(), make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "1000:ready",
            "1000:ready",
        ]

    def test_setup_code_does_not_gain_line_namespace_later(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody("def describe(): return line.start"),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!describe()!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ],
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_processes_karaoke_effect_lines_without_k_tags(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("L"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )
        plain_karaoke_event = Event(
            text="plain text",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1500,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )

        results = engine.apply(
            [plain_karaoke_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["L"]

    def test_supports_multiple_named_loops_in_cartesian_order(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("A$loop_a_i-B$loop_b_i"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        when="syl.i == 0",
                        loops=(
                            LoopDescriptor(
                                name="a",
                                iterations=2,
                                explicit_name="a",
                            ),
                            LoopDescriptor(
                                name="b",
                                iterations=3,
                                explicit_name="b",
                            ),
                        ),
                    ),
                )
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "A0-B0go",
            "A0-B1go",
            "A0-B2go",
            "A1-B0go",
            "A1-B1go",
            "A1-B2go",
        ]

    def test_loop_i_is_invalid_when_multiple_loops_are_visible(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("$loop_i"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        when="syl.i == 0",
                        loops=(
                            LoopDescriptor(
                                name="a",
                                iterations=2,
                                explicit_name="a",
                            ),
                            LoopDescriptor(
                                name="b",
                                iterations=2,
                                explicit_name="b",
                            ),
                        ),
                    ),
                )
            ]
        )

        with pytest.raises(UnknownVariableError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_line_loop_is_visible_to_syl_and_char(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("L$loop_i"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        no_text=True,
                        loops=(LoopDescriptor(name="i", iterations=2),),
                    ),
                )
            ],
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("S$loop_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=False),
                )
            ],
            char=[
                TemplateDeclaration(
                    body=TemplateBody("C$loop_i-$char_x:"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(no_text=False),
                )
            ],
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "L0",
            "S0:go",
            "C0-955:g",
            "C0-965:o",
            "L1",
            "S1:go",
            "C1-955:g",
            "C1-965:o",
        ]

    def test_syl_loop_is_visible_to_char(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("S$loop_wave_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        when="syl.i == 0",
                        loops=(
                            LoopDescriptor(
                                name="wave",
                                iterations=2,
                                explicit_name="wave",
                            ),
                        ),
                    ),
                )
            ],
            char=[
                TemplateDeclaration(
                    body=TemplateBody("C$loop_wave_i-$char_x:"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(
                        no_text=False,
                        when="syl.i == 0",
                    ),
                )
            ],
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "S0:go",
            "C0-955:g",
            "C0-965:o",
            "S1:go",
            "C1-955:g",
            "C1-965:o",
        ]

    def test_honors_no_blank_modifier(self) -> None:
        engine = build_engine()
        blank_event = Event(
            text=r"{\k20}  {\k30}go",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1500,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("X"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_blank=True),
                )
            ]
        )

        results = engine.apply(
            [blank_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["Xgo"]

    def test_honors_line_no_blank_modifier(self) -> None:
        engine = build_engine()
        blank_event = Event(
            text=r"{\k20}  ",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1200,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("X"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_blank=True),
                )
            ]
        )

        results = engine.apply(
            [blank_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert results == []

    def test_honors_fx_modifier(self) -> None:
        engine = build_engine()
        fx_event = Event(
            text=r"{\k20\-flash}go{\k30}al",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1500,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("F"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(fx="flash"),
                )
            ]
        )

        results = engine.apply(
            [fx_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["Fgo", "Fal"]

    def test_multi_highlight_is_processed_once_per_merged_syllable(
        self,
    ) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k10}go{\k20}#al",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1300,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("M"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["Mgo"]

    def test_renders_namespaced_retime_target(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.syl(10, 20)!S"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [(result.start_time, result.end_time) for result in results] == [
            (1010, 1220),
            (1210, 1520),
        ]

    def test_renders_line_preset_over_chars(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            char=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.line.ltr(-300, 0)!C"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [(result.start_time, result.end_time) for result in results] == [
            (700, 1500),
            (800, 1500),
            (900, 1500),
            (1000, 1500),
        ]

    def test_rejects_preset_in_line_scope(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.line.ltr(-300, 0)!L"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_rejects_multiple_retime_calls_per_template(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.line()!!retime.syl()!S"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_raises_on_callable_saved_by_set(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                CodeDeclaration(
                    body=CodeBody("set('bad', layer.set)"),
                    scope=Scope.SYL,
                )
            ]
        )

        with pytest.raises(BoundMethodInExpressionError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )
