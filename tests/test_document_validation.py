"""Integration tests for phase 12 cross and document validation."""

from __future__ import annotations

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Metadata, Style
from pykara.declaration import Scope
from pykara.declaration.code import CodeBody
from pykara.declaration.patch import PatchBody, PatchModifiers
from pykara.declaration.template import TemplateBody, TemplateModifiers
from pykara.parsing import (
    CodeDeclaration,
    ParsedDeclarations,
    PatchDeclaration,
    TemplateDeclaration,
)
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


def make_patch_declaration(
    *,
    text: str = "{\\bord4}",
    scope: Scope = Scope.SYL,
    modifiers: PatchModifiers | None = None,
    actor: str = "lead",
) -> PatchDeclaration:
    return PatchDeclaration(
        body=PatchBody(text),
        scope=scope,
        modifiers=modifiers or PatchModifiers(),
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

    def test_accepts_patch_with_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            patch_syl=[make_patch_declaration(actor="unrelated")],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_reports_patch_for_actor_without_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            patch_syl=[
                make_patch_declaration(
                    modifiers=PatchModifiers(for_actor="missing")
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.patch_template_compatible",
        )

    def test_reports_patch_without_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            patch_word=[make_patch_declaration(scope=Scope.WORD)],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.patch_template_compatible",
        )

    def test_reports_patch_variable_used_outside_scope(self) -> None:
        declarations = ParsedDeclarations(
            line=[make_template_declaration(scope=Scope.LINE)],
            patch_line=[
                make_patch_declaration(text="$syl_x", scope=Scope.LINE)
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

    def test_parses_and_validates_karaoke_syllables(self) -> None:
        document = make_document(events=[make_event(text="{\\k20}   ")])

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert tuple(violation.code for violation in report.violations) == (
            "karaoke.timed_text_required",
        )

    def test_skips_non_karaoke_events_for_karaoke_validation(self) -> None:
        document = make_document(events=[make_event(text="plain text")])

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()
