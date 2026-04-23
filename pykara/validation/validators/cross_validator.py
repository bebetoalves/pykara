"""Validator for cross-document and cross-declaration rules."""

from __future__ import annotations

from collections.abc import Iterable

from pykara.adapters import SubtitleDocument
from pykara.parsing import (
    CodeDeclaration,
    MixinDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.validation.reports import ValidationReport, Violation
from pykara.validation.rules.cross_rules import (
    AllowedVariableScopeRule,
    BareStringArgumentReference,
    CodeVariableDeclaration,
    EventStyleReference,
    ExistingStyleRule,
    FxModifierScopeRule,
    FxModifierUsage,
    MixinTemplateCompatibilityRule,
    MixinTemplateReference,
    QuotedStringArgumentRule,
    TemplateVariableReference,
    UsedCodeVariableRule,
    iter_bare_string_argument_references,
    iter_code_bare_string_argument_references,
    iter_code_declared_variables,
    iter_code_variable_references,
    iter_template_code_variable_references,
    iter_template_variables,
)


class CrossValidator:
    """Validate relationships that span the document and declarations."""

    def __init__(self) -> None:
        self._style_rule = ExistingStyleRule()
        self._variable_scope_rule = AllowedVariableScopeRule()
        self._quoted_string_argument_rule = QuotedStringArgumentRule()
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
            *self._validate_quoted_string_arguments(declarations),
            *self._validate_code_variable_usage(declarations),
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

    def _validate_quoted_string_arguments(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        return tuple(
            violation
            for reference in self._iter_bare_string_argument_references(
                declarations
            )
            if (violation := self._quoted_string_argument_rule.check(reference))
            is not None
        )

    def _validate_code_variable_usage(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        used_names = frozenset(
            self._iter_used_code_variable_names(declarations)
        )
        rule = UsedCodeVariableRule(used_names=used_names)
        return tuple(
            violation
            for declaration in self._iter_code_declarations(declarations)
            for variable_name in iter_code_declared_variables(declaration)
            if (
                violation := rule.check(
                    CodeVariableDeclaration(
                        declaration=declaration,
                        variable_name=variable_name,
                    )
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

    def _iter_bare_string_argument_references(
        self,
        declarations: ParsedDeclarations,
    ) -> Iterable[BareStringArgumentReference]:
        for declaration in (
            *self._iter_template_declarations(declarations),
            *self._iter_mixin_declarations(declarations),
            *self._iter_code_declarations(declarations),
        ):
            if isinstance(declaration, CodeDeclaration):
                yield from iter_code_bare_string_argument_references(
                    declaration
                )
            else:
                yield from iter_bare_string_argument_references(declaration)

    def _iter_used_code_variable_names(
        self,
        declarations: ParsedDeclarations,
    ) -> Iterable[str]:
        for declaration in self._iter_code_declarations(declarations):
            yield from iter_code_variable_references(declaration)

        for declaration in (
            *self._iter_template_declarations(declarations),
            *self._iter_mixin_declarations(declarations),
        ):
            yield from iter_template_code_variable_references(declaration)

    def _iter_code_declarations(
        self,
        declarations: ParsedDeclarations,
    ) -> Iterable[CodeDeclaration]:
        yield from declarations.setup
        for declaration in declarations.line:
            if isinstance(declaration, CodeDeclaration):
                yield declaration

        for declaration in declarations.syl:
            if isinstance(declaration, CodeDeclaration):
                yield declaration

        for declaration in declarations.word:
            if isinstance(declaration, CodeDeclaration):
                yield declaration
