"""Parser for template and code declaration events."""

from __future__ import annotations

from dataclasses import dataclass, field

from pykara.data import Event
from pykara.declaration import Scope
from pykara.declaration._shared import ModifierRegistry
from pykara.declaration.code import CodeBody
from pykara.declaration.template import TemplateBody, TemplateModifiers
from pykara.errors import (
    DeclarativeParseError,
    InternalConsistencyError,
    UnknownModifierError,
)
from pykara.specification import DECLARATIONS, SCOPE_SPECIFICATIONS


def _empty_code_declarations() -> list[CodeDeclaration]:
    return []


def _empty_scoped_declarations() -> list[TemplateDeclaration | CodeDeclaration]:
    return []


def _empty_template_declarations() -> list[TemplateDeclaration]:
    return []


def _empty_active_styles() -> set[str]:
    return set()


@dataclass(frozen=True, slots=True)
class TemplateDeclaration:
    """One parsed template declaration."""

    body: TemplateBody
    scope: Scope
    modifiers: TemplateModifiers
    style: str = ""


@dataclass(frozen=True, slots=True)
class CodeDeclaration:
    """One parsed code declaration."""

    body: CodeBody
    scope: Scope
    style: str = ""


@dataclass(slots=True)
class ParsedDeclarations:
    """Parsed declarations grouped by execution scope."""

    init: list[CodeDeclaration] = field(
        default_factory=_empty_code_declarations
    )
    line: list[TemplateDeclaration | CodeDeclaration] = field(
        default_factory=_empty_scoped_declarations
    )
    word: list[TemplateDeclaration | CodeDeclaration] = field(
        default_factory=_empty_scoped_declarations
    )
    syl: list[TemplateDeclaration | CodeDeclaration] = field(
        default_factory=_empty_scoped_declarations
    )
    char: list[TemplateDeclaration] = field(
        default_factory=_empty_template_declarations
    )
    active_styles: set[str] = field(default_factory=_empty_active_styles)


class DeclarationParser:
    """Parse commented declaration events into normalized objects."""

    def __init__(
        self,
        template_mod_registry: ModifierRegistry[TemplateModifiers],
    ) -> None:
        self._template_mod_registry = template_mod_registry

    def parse(self, events: list[Event]) -> ParsedDeclarations:
        """Parse template and code declarations from commented events.

        Args:
            events: Domain events to inspect.

        Returns:
            Declarations grouped by execution scope.

        Raises:
            DeclarativeParseError: If a declaration lacks an explicit scope
                or contains unsupported tokens.
        """

        parsed = ParsedDeclarations()

        for event in events:
            declaration = self._parse_event(event)
            if declaration is None:
                continue

            parsed.active_styles.add(event.style)
            self._append_declaration(parsed, declaration)

        return parsed

    def _parse_event(
        self, event: Event
    ) -> TemplateDeclaration | CodeDeclaration | None:
        """Parse one event when it contains a supported declaration."""

        if not event.comment:
            return None

        effect_tokens = event.effect.split()
        if not effect_tokens:
            return None

        declaration_name = effect_tokens[0].lower()
        declaration_spec = DECLARATIONS.get(declaration_name)
        if declaration_spec is None:
            return None

        scope, remaining_tokens = self._parse_scope(
            declaration_name=declaration_name,
            effect_field=event.effect,
            tokens=effect_tokens[1:],
        )
        if scope not in declaration_spec.allowed_scopes:
            raise DeclarativeParseError(
                effect_field=event.effect,
                message=(
                    f"Scope {scope.value!r} is not allowed for "
                    f"{declaration_name!r}"
                ),
            )

        declaration_style, remaining_tokens = self._parse_style_selector(
            event=event,
            remaining_tokens=remaining_tokens,
        )

        if declaration_name == "template":
            modifiers = self._parse_template_modifiers(
                effect_field=event.effect,
                tokens=remaining_tokens,
            )
            return TemplateDeclaration(
                body=TemplateBody(event.text),
                scope=scope,
                modifiers=modifiers,
                style=declaration_style,
            )

        if remaining_tokens:
            unexpected = remaining_tokens[0]
            raise DeclarativeParseError(
                effect_field=event.effect,
                message=(f"Unexpected token after code scope: {unexpected!r}"),
            )

        return CodeDeclaration(
            body=CodeBody(event.text),
            scope=scope,
            style=declaration_style,
        )

    def _parse_style_selector(
        self,
        *,
        event: Event,
        remaining_tokens: list[str],
    ) -> tuple[str, list[str]]:
        """Return the declaration style filter and unconsumed tokens."""

        if remaining_tokens and remaining_tokens[0].lower() == "all":
            return "", remaining_tokens[1:]

        return event.style, remaining_tokens

    def _parse_scope(
        self,
        *,
        declaration_name: str,
        effect_field: str,
        tokens: list[str],
    ) -> tuple[Scope, list[str]]:
        """Parse and validate the explicit declaration scope."""

        if not tokens:
            raise DeclarativeParseError(
                effect_field=effect_field,
                message=(
                    f"{declaration_name!r} declaration requires "
                    "an explicit scope"
                ),
            )

        scope_token = tokens[0].lower()
        scope = self._scope_from_token(scope_token)
        if scope is None:
            raise DeclarativeParseError(
                effect_field=effect_field,
                message=(
                    f"Invalid scope {scope_token!r} for {declaration_name!r}"
                ),
            )

        return scope, tokens[1:]

    def _parse_template_modifiers(
        self,
        *,
        effect_field: str,
        tokens: list[str],
    ) -> TemplateModifiers:
        """Parse template modifiers through the injected registry."""

        try:
            return self._template_mod_registry.parse(tokens)
        except UnknownModifierError as error:
            raise DeclarativeParseError(
                effect_field=effect_field,
                message=(
                    f"Unexpected token after template scope: {error.modifier!r}"
                ),
            ) from error

    def _scope_from_token(self, token: str) -> Scope | None:
        """Resolve one scope token using the shared specifications."""

        for scope in SCOPE_SPECIFICATIONS:
            if scope.value == token:
                return scope
        return None

    def _append_declaration(
        self,
        parsed: ParsedDeclarations,
        declaration: TemplateDeclaration | CodeDeclaration,
    ) -> None:
        """Append one parsed declaration to the matching scope bucket."""

        if declaration.scope is Scope.INIT:
            if not isinstance(declaration, CodeDeclaration):
                message = "INIT scope is only valid for code declarations."
                raise InternalConsistencyError(message)
            parsed.init.append(declaration)
            return

        if declaration.scope is Scope.LINE:
            parsed.line.append(declaration)
            return

        if declaration.scope is Scope.WORD:
            parsed.word.append(declaration)
            return

        if declaration.scope is Scope.SYL:
            parsed.syl.append(declaration)
            return

        if not isinstance(declaration, TemplateDeclaration):
            message = "CHAR scope is only valid for template declarations."
            raise InternalConsistencyError(message)
        parsed.char.append(declaration)
