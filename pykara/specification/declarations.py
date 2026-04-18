"""Public declaration-level language contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.declaration import Scope


@dataclass(frozen=True, slots=True)
class DeclarationSpecification:
    """Describe one declaration type supported by the language."""

    name: str
    allowed_scopes: frozenset[Scope]
    allowed_modifiers: frozenset[str]
    description: str


TEMPLATE_DECLARATION = DeclarationSpecification(
    name="template",
    allowed_scopes=frozenset({Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}),
    allowed_modifiers=frozenset(
        {"loop", "no_blank", "no_text", "fx", "when", "unless"}
    ),
    description="Generate effect lines from parameterized text.",
)

CODE_DECLARATION = DeclarationSpecification(
    name="code",
    allowed_scopes=frozenset({Scope.SETUP, Scope.LINE, Scope.WORD, Scope.SYL}),
    allowed_modifiers=frozenset(),
    description="Execute Python code in the execution environment.",
)

DECLARATIONS: dict[str, DeclarationSpecification] = {
    TEMPLATE_DECLARATION.name: TEMPLATE_DECLARATION,
    CODE_DECLARATION.name: CODE_DECLARATION,
}
