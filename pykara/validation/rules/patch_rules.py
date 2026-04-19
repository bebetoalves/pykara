"""Validation rules for parsed patch declarations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pykara.parsing import PatchDeclaration
from pykara.specification import DECLARATIONS, MODIFIER_SPECIFICATIONS
from pykara.validation.reports import Severity, Violation

INLINE_EXPRESSION_PATTERN = re.compile(r"!(.+?)!", re.DOTALL)
UNSUPPORTED_INLINE_MARKERS = (
    re.compile(r"\bfunction\b"),
    re.compile(r"\.\."),
    re.compile(r"\blocal\b"),
    re.compile(r"#\w+"),
)


def contains_unsupported_inline_marker(source: str) -> bool:
    """Return whether an inline expression contains unsupported syntax."""

    return any(
        pattern.search(source) is not None
        for pattern in UNSUPPORTED_INLINE_MARKERS
    )


def _iter_active_modifiers(
    declaration: PatchDeclaration,
) -> tuple[str, ...]:
    modifiers = declaration.modifiers
    active_modifiers: list[str] = []

    if modifiers.prepend:
        active_modifiers.append("prepend")
    if modifiers.layer is not None:
        active_modifiers.append("layer")
    if modifiers.for_actor is not None:
        active_modifiers.append("for")
    if modifiers.fx is not None:
        active_modifiers.append("fx")
    if modifiers.when is not None:
        active_modifiers.append("when")
    if modifiers.unless is not None:
        active_modifiers.append("unless")

    return tuple(active_modifiers)


@dataclass(frozen=True, slots=True)
class PatchAllowedScopeRule:
    """Ensure patch declarations use one of the documented scopes."""

    code: str = "patch.scope_allowed"
    severity: Severity = Severity.ERROR

    def check(self, subject: PatchDeclaration) -> Violation | None:
        allowed_scopes = DECLARATIONS["patch"].allowed_scopes
        if subject.scope in allowed_scopes:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Patch declaration uses an unsupported scope.",
            context=f"scope={subject.scope.value!r}",
            location="patch.scope",
        )


@dataclass(frozen=True, slots=True)
class PatchPythonExpressionSyntaxRule:
    """Reject unsupported syntax inside inline patch expressions."""

    code: str = "patch.expression_python_only"
    severity: Severity = Severity.ERROR

    def check(self, subject: PatchDeclaration) -> Violation | None:
        for match in INLINE_EXPRESSION_PATTERN.finditer(subject.body.text):
            expression = match.group(1)
            if not contains_unsupported_inline_marker(expression):
                continue

            return Violation(
                severity=self.severity,
                code=self.code,
                message=(
                    "Patch inline expressions must use Python syntax, "
                    "not unsupported expression syntax."
                ),
                context=f"expression={expression!r}",
                location="patch.body",
            )
        return None


@dataclass(frozen=True, slots=True)
class CompatiblePatchModifierScopeRule:
    """Ensure active patch modifiers are valid for the current scope."""

    code: str = "patch.modifier_scope_compatible"
    severity: Severity = Severity.ERROR

    def check(self, subject: PatchDeclaration) -> Violation | None:
        for modifier_name in _iter_active_modifiers(subject):
            specification = MODIFIER_SPECIFICATIONS[modifier_name]
            if "patch" not in specification.applicable_to:
                return Violation(
                    severity=self.severity,
                    code=self.code,
                    message="Patch modifier is not available for patches.",
                    context=f"modifier={modifier_name!r}",
                    location="patch.modifiers",
                )
            if subject.scope in specification.allowed_scopes:
                continue

            return Violation(
                severity=self.severity,
                code=self.code,
                message="Patch modifier is not allowed for this scope.",
                context=(
                    f"modifier={modifier_name!r}, scope={subject.scope.value!r}"
                ),
                location="patch.modifiers",
            )
        return None
