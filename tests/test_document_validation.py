"""Integration tests for phase 12 cross and document validation."""

from __future__ import annotations

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Metadata, Style
from pykara.declaration import Scope
from pykara.declaration.code import CodeBody
from pykara.declaration.mixin import MixinBody, MixinModifiers
from pykara.declaration.template import TemplateBody, TemplateModifiers
from pykara.parsing import (
    CodeDeclaration,
    MixinDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.validation.reports import ValidationReport
from pykara.validation.validators import CrossValidator, DocumentValidator


def make_style() -> Style:
    return Style(
        name="Default",
        fontname="Arial",
        fontsize=42.0,
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


def make_event(
    *,
    text: str = "{\\k20}ka",
    effect: str = "karaoke",
    style: str = "Default",
    comment: bool = False,
) -> Event:
    return Event(
        text=text,
        effect=effect,
        style=style,
        layer=0,
        start_time=100,
        end_time=400,
        comment=comment,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_template_declaration(
    *,
    text: str = "{\\pos($line_left,$line_top)}",
    scope: Scope = Scope.SYL,
    modifiers: TemplateModifiers | None = None,
) -> TemplateDeclaration:
    return TemplateDeclaration(
        body=TemplateBody(text),
        scope=scope,
        modifiers=modifiers or TemplateModifiers(),
        actor="lead",
    )


def make_mixin_declaration(
    *,
    text: str = "{\\bord4}",
    scope: Scope = Scope.SYL,
    modifiers: MixinModifiers | None = None,
    actor: str = "lead",
) -> MixinDeclaration:
    return MixinDeclaration(
        body=MixinBody(text),
        scope=scope,
        modifiers=modifiers or MixinModifiers(),
        actor=actor,
    )


def make_code_declaration(
    *,
    source: str = "counter = 1",
    scope: Scope = Scope.SYL,
) -> CodeDeclaration:
    return CodeDeclaration(body=CodeBody(source), scope=scope)


def make_document(*, events: list[Event] | None = None) -> SubtitleDocument:
    style = make_style()
    return SubtitleDocument(
        metadata=Metadata(res_x=1920, res_y=1080),
        styles={style.name: style},
        events=events or [make_event()],
    )


class TestCrossValidator:
    def test_accepts_valid_document_and_declarations(self) -> None:
        document = make_document()
        declarations = ParsedDeclarations(
            syl=[make_template_declaration(text="{\\pos($syl_x,$syl_y)}")]
        )

        report = CrossValidator().validate(document, declarations)

        assert report.violations == ()

    def test_reports_missing_style_reference(self) -> None:
        document = make_document(events=[make_event(style="Missing")])

        report = CrossValidator().validate(document, ParsedDeclarations())

        assert tuple(violation.code for violation in report.violations) == (
            "cross.style_exists",
        )

    def test_reports_syl_variable_used_in_line_scope(self) -> None:
        declarations = ParsedDeclarations(
            line=[
                make_template_declaration(
                    text="{\\pos($syl_x,$syl_y)}",
                    scope=Scope.LINE,
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.variable_scope_allowed",
            "cross.variable_scope_allowed",
        )

    def test_reports_char_variable_used_in_syl_scope(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text="char=$char_x",
                    scope=Scope.SYL,
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.variable_scope_allowed",
        )

    def test_accepts_quoted_string_arguments(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text=(
                        "!set('name', 123)!!lock('name', 123)!"
                        "!get('name')!"
                        "!color.interpolate(0.5, '&H000000&', '&HFFFFFF&')!"
                    ),
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_reports_bare_string_arguments(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text=(
                        "!set(name, 123)!!lock(name, 123)!!get(name)!"
                        "!color.interpolate(0.5, red, blue)!"
                    ),
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
        )
        assert tuple(violation.context for violation in report.violations) == (
            "function='set', argument='key', value='name', scope=syl",
            "function='lock', argument='key', value='name', scope=syl",
            "function='get', argument='key', value='name', scope=syl",
            (
                "function='color.interpolate', argument='start_color', "
                "value='red', scope=syl"
            ),
            (
                "function='color.interpolate', argument='end_color', "
                "value='blue', scope=syl"
            ),
        )

    def test_reports_bare_string_arguments_in_code_declarations(self) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source="value = color.interpolate(0.5, red, blue)",
                    scope=Scope.SETUP,
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
        )
        assert tuple(violation.context for violation in report.violations) == (
            (
                "function='color.interpolate', argument='start_color', "
                "value='red', scope=setup"
            ),
            (
                "function='color.interpolate', argument='end_color', "
                "value='blue', scope=setup"
            ),
        )

    def test_reports_fx_modifier_outside_syl_scope(self) -> None:
        declarations = ParsedDeclarations(
            line=[
                make_template_declaration(
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(fx="flash"),
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.fx_scope_allowed",
        )

    def test_accepts_mixin_with_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            mixin_syl=[make_mixin_declaration(actor="unrelated")],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_reports_mixin_for_actor_without_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            mixin_syl=[
                make_mixin_declaration(
                    modifiers=MixinModifiers(for_actor="missing")
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.mixin_template_compatible",
        )

    def test_reports_mixin_without_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            mixin_word=[make_mixin_declaration(scope=Scope.WORD)],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.mixin_template_compatible",
        )

    def test_reports_mixin_variable_used_outside_scope(self) -> None:
        declarations = ParsedDeclarations(
            line=[make_template_declaration(scope=Scope.LINE)],
            mixin_line=[
                make_mixin_declaration(text="$syl_x", scope=Scope.LINE)
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.variable_scope_allowed",
        )


class TestDocumentValidator:
    def test_aggregates_cross_rule_violations(self) -> None:
        document = make_document(events=[make_event(style="Missing")])
        declarations = ParsedDeclarations(
            line=[
                make_template_declaration(
                    text="{\\pos($syl_x,$syl_y)}",
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(fx="flash"),
                ),
                make_code_declaration(scope=Scope.LINE),
            ]
        )

        report = DocumentValidator().validate(document, declarations)

        assert "cross.style_exists" in {
            violation.code for violation in report.violations
        }
        assert "cross.variable_scope_allowed" in {
            violation.code for violation in report.violations
        }
        assert "cross.fx_scope_allowed" in {
            violation.code for violation in report.violations
        }

    def test_accepts_timed_blank_karaoke_syllables(self) -> None:
        document = make_document(events=[make_event(text="{\\k20}   ")])

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_accepts_consecutive_leading_karaoke_tags_as_blank_syllable(
        self,
    ) -> None:
        document = make_document(
            events=[
                make_event(
                    text=(
                        "{\\k23}{\\k22}ka{\\k25}na{\\k77}shii "
                        "{\\k25}to{\\k43}ki"
                    )
                )
            ]
        )

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_accepts_zero_duration_karaoke_syllable_in_dialogue(self) -> None:
        document = make_document(
            events=[
                make_event(
                    text=r"{\k46}bomb{\k0}-{\k91}bomb {\k24}dan{\k65}cin'"
                )
            ]
        )

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_accepts_zero_duration_karaoke_syllable_in_comment(self) -> None:
        document = make_document(
            events=[
                make_event(
                    text=r"{\k46}bomb{\k0}-{\k91}bomb {\k24}dan{\k65}cin'",
                    comment=True,
                )
            ]
        )

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_validates_commented_karaoke_same_as_dialogue(self) -> None:
        class RecordingDocumentValidator(DocumentValidator):
            def __init__(self) -> None:
                super().__init__()
                self.seen_comments: list[bool] = []

            def _validate_event_karaoke(self, event: Event) -> ValidationReport:
                self.seen_comments.append(event.comment)
                return super()._validate_event_karaoke(event)

        validator = RecordingDocumentValidator()
        validator.validate(
            make_document(events=[make_event(text=r"{\k0}-", comment=False)]),
            ParsedDeclarations(),
        )
        validator.validate(
            make_document(events=[make_event(text=r"{\k0}-", comment=True)]),
            ParsedDeclarations(),
        )

        assert validator.seen_comments == [False, True]

    def test_ignores_k_tags_when_effect_is_not_karaoke(self) -> None:
        document = make_document(
            events=[make_event(text=r"{\k0}-", effect="", comment=False)]
        )

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_validates_ko_tags_for_karaoke_events(self) -> None:
        document = make_document(events=[make_event(text=r"{\ko0}go")])

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_skips_non_karaoke_events_for_karaoke_validation(self) -> None:
        document = make_document(events=[make_event(text="plain text")])

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()
