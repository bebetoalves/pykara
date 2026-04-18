"""Cross-domain validation rules that inspect document relationships."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pykara.data import Event
from pykara.parsing import TemplateDeclaration
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

    declaration: TemplateDeclaration
    variable_name: str


@dataclass(frozen=True, slots=True)
class FxModifierUsage:
    """One template declaration using the fx modifier."""

    declaration: TemplateDeclaration


def iter_template_variables(
    declaration: TemplateDeclaration,
) -> tuple[str, ...]:
    """Return all `$var` references found inside a template body."""

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
            message=(
                "Template variable is not available in this declaration scope."
            ),
            context=(
                f"variable=${subject.variable_name}, "
                f"group={variable_specification.group}, "
                f"scope={subject.declaration.scope.value}"
            ),
            location="template.body",
        )


@dataclass(frozen=True, slots=True)
class FxModifierScopeRule:
    """Ensure the fx modifier is only used by syllable templates."""

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
            location="template.modifiers.fx",
        )
