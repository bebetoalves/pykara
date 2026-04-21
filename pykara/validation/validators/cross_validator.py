"""Validator for cross-document and cross-declaration rules."""

from __future__ import annotations

from collections.abc import Iterable

from pykara.adapters import SubtitleDocument
from pykara.parsing import (
    MixinDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.validation.reports import ValidationReport, Violation
from pykara.validation.rules.cross_rules import (
    AllowedVariableScopeRule,
    EventStyleReference,
    ExistingStyleRule,
    FxModifierScopeRule,
    FxModifierUsage,
    MixinTemplateCompatibilityRule,
    MixinTemplateReference,
    TemplateVariableReference,
    iter_template_variables,
)


class CrossValidator:
    """Validate relationships that span the document and declarations."""

    def __init__(self) -> None:
        self._style_rule = ExistingStyleRule()
        self._variable_scope_rule = AllowedVariableScopeRule()
        self._fx_scope_rule = FxModifierScopeRule()
        self._mixin_template_rule = MixinTemplateCompatibilityRule()

    def validate(
        self,
        document: SubtitleDocument,
        declarations: ParsedDeclarations,
    ) -> ValidationReport:
        """Validate relationships that span document and declaration data.

        Args:
            document: Loaded subtitle document.
            declarations: Parsed declarations for that document.

        Returns:
            Validation report for cross-cutting rules.
        """
        violations = (
            *self._validate_style_references(document),
            *self._validate_template_variables(declarations),
            *self._validate_mixin_variables(declarations),
            *self._validate_fx_usage(declarations),
            *self._validate_mixin_template_usage(declarations),
        )
        return ValidationReport(violations)

    def _validate_style_references(
        self,
        document: SubtitleDocument,
    ) -> tuple[Violation, ...]:
        available_styles = frozenset(document.styles)
        return tuple(
            violation
            for event in document.events
            if (
                violation := self._style_rule.check(
                    EventStyleReference(
                        event=event,
                        available_styles=available_styles,
                    )
                )
            )
            is not None
        )

    def _validate_template_variables(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        return tuple(
            violation
            for declaration in self._iter_template_declarations(declarations)
            for variable_name in iter_template_variables(declaration)
            if (
                violation := self._variable_scope_rule.check(
                    TemplateVariableReference(
                        declaration=declaration,
                        variable_name=variable_name,
                    )
                )
            )
            is not None
        )

    def _validate_fx_usage(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        return tuple(
            violation
            for declaration in (
                *self._iter_template_declarations(declarations),
                *self._iter_mixin_declarations(declarations),
            )
            if declaration.modifiers.fx is not None
            if (
                violation := self._fx_scope_rule.check(
                    FxModifierUsage(declaration=declaration)
                )
            )
            is not None
        )

    def _validate_mixin_variables(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        return tuple(
            violation
            for declaration in self._iter_mixin_declarations(declarations)
            for variable_name in iter_template_variables(declaration)
            if (
                violation := self._variable_scope_rule.check(
                    TemplateVariableReference(
                        declaration=declaration,
                        variable_name=variable_name,
                    )
                )
            )
            is not None
        )

    def _validate_mixin_template_usage(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        templates = tuple(self._iter_template_declarations(declarations))
        return tuple(
            violation
            for declaration in self._iter_mixin_declarations(declarations)
            if (
                violation := self._mixin_template_rule.check(
                    MixinTemplateReference(
                        mixin=declaration,
                        templates=templates,
                    )
                )
            )
            is not None
        )

    def _iter_template_declarations(
        self,
        declarations: ParsedDeclarations,
    ) -> Iterable[TemplateDeclaration]:
        for declaration in declarations.line:
            if isinstance(declaration, TemplateDeclaration):
                yield declaration

        for declaration in declarations.syl:
            if isinstance(declaration, TemplateDeclaration):
                yield declaration

        for declaration in declarations.word:
            if isinstance(declaration, TemplateDeclaration):
                yield declaration

        yield from declarations.char

    def _iter_mixin_declarations(
        self,
        declarations: ParsedDeclarations,
    ) -> Iterable[MixinDeclaration]:
        yield from declarations.mixin_line
        yield from declarations.mixin_word
        yield from declarations.mixin_syl
        yield from declarations.mixin_char
