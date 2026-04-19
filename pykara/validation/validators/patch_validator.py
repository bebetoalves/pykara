"""Concrete validator for patch declarations."""

from __future__ import annotations

from collections.abc import Sequence

from pykara.parsing import PatchDeclaration
from pykara.validation.rules._base import Rule
from pykara.validation.rules.patch_rules import (
    CompatiblePatchModifierScopeRule,
    PatchAllowedScopeRule,
    PatchPythonExpressionSyntaxRule,
)
from pykara.validation.validators._base import RuleBasedValidator


class PatchValidator(RuleBasedValidator[PatchDeclaration]):
    """Validate patch declarations using patch-specific domain rules."""

    def __init__(
        self,
        rules: Sequence[Rule[PatchDeclaration]] | None = None,
    ) -> None:
        super().__init__(
            rules
            or (
                PatchAllowedScopeRule(),
                PatchPythonExpressionSyntaxRule(),
                CompatiblePatchModifierScopeRule(),
            )
        )
