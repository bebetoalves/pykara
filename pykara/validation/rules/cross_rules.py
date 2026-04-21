"""Cross-domain validation rules that inspect document relationships."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pykara.data import Event
from pykara.parsing import MixinDeclaration, TemplateDeclaration
from pykara.specification import (
    MODIFIER_SPECIFICATIONS,
    SCOPE_SPECIFICATIONS,
    VARIABLE_SPECIFICATIONS,
)
from pykara.validation.reports import Severity, Violation

_TEMPLATE_VARIABLE_PATTERN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


@dataclass(frozen=True, slots=True)
class EventStyleReference:
    """One event-style reference to validate against the document styles."""

    event: Event
    available_styles: frozenset[str]


@dataclass(frozen=True, slots=True)
class TemplateVariableReference:
    """One variable reference found inside a template body."""

    declaration: TemplateDeclaration | MixinDeclaration
    variable_name: str


@dataclass(frozen=True, slots=True)
class FxModifierUsage:
    """One declaration using the fx modifier."""

    declaration: TemplateDeclaration | MixinDeclaration


@dataclass(frozen=True, slots=True)
class MixinTemplateReference:
    """One mixin declaration to validate against template declarations."""

    mixin: MixinDeclaration
    templates: tuple[TemplateDeclaration, ...]


def iter_template_variables(
    declaration: TemplateDeclaration | MixinDeclaration,
) -> tuple[str, ...]:
    """Return all `$var` references found inside a template or mixin body."""

    return tuple(_TEMPLATE_VARIABLE_PATTERN.findall(declaration.body.text))


@dataclass(frozen=True, slots=True)
class ExistingStyleRule:
    """Ensure referenced event styles exist in the document."""

    code: str = "cross.style_exists"
    severity: Severity = Severity.ERROR

    def check(self, subject: EventStyleReference) -> Violation | None:
        if subject.event.style in subject.available_styles:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Event style must exist in the document style map.",
            context=(
                f"style={subject.event.style!r}, "
                f"effect={subject.event.effect!r}"
            ),
            location="event.style",
        )


@dataclass(frozen=True, slots=True)
class AllowedVariableScopeRule:
    """Ensure template variables belong to the current declaration scope."""

    code: str = "cross.variable_scope_allowed"
    severity: Severity = Severity.ERROR

    def check(self, subject: TemplateVariableReference) -> Violation | None:
        variable_specification = VARIABLE_SPECIFICATIONS.get(
            subject.variable_name
        )
        if variable_specification is None:
            return None

        allowed_groups = SCOPE_SPECIFICATIONS[
            subject.declaration.scope
        ].variable_groups
        if variable_specification.group in allowed_groups:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message=("Variable is not available in this declaration scope."),
            context=(
                f"variable=${subject.variable_name}, "
                f"group={variable_specification.group}, "
                f"scope={subject.declaration.scope.value}"
            ),
            location="declaration.body",
        )


@dataclass(frozen=True, slots=True)
class FxModifierScopeRule:
    """Ensure the fx modifier is only used by syllable declarations."""

    code: str = "cross.fx_scope_allowed"
    severity: Severity = Severity.ERROR

    def check(self, subject: FxModifierUsage) -> Violation | None:
        allowed_scopes = MODIFIER_SPECIFICATIONS["fx"].allowed_scopes
        if subject.declaration.scope in allowed_scopes:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="The fx modifier is only available in syllable scope.",
            context=f"scope={subject.declaration.scope.value!r}",
            location="declaration.modifiers.fx",
        )


@dataclass(frozen=True, slots=True)
class MixinTemplateCompatibilityRule:
    """Ensure every mixin has at least one compatible active template."""

    code: str = "cross.mixin_template_compatible"
    severity: Severity = Severity.ERROR

    def check(self, subject: MixinTemplateReference) -> Violation | None:
        if any(
            self._is_compatible(subject.mixin, template)
            for template in subject.templates
        ):
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message=(
                "Mixin declaration must target at least one compatible "
                "template with the same scope and style."
            ),
            context=(
                f"scope={subject.mixin.scope.value!r}, "
                f"style={subject.mixin.style!r}, "
                f"for_actor={subject.mixin.modifiers.for_actor!r}"
            ),
            location="mixin",
        )

    def _is_compatible(
        self,
        mixin: MixinDeclaration,
        template: TemplateDeclaration,
    ) -> bool:
        if mixin.scope is not template.scope:
            return False
        if template.style and template.style != mixin.style:
            return False
        if mixin.modifiers.for_actor is None:
            return True
        return template.actor == mixin.modifiers.for_actor
