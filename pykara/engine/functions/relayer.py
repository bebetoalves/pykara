"""Relayer function."""

from __future__ import annotations

from typing import ClassVar, Protocol, cast


class _RelayerLine(Protocol):
    layer: int


class _RelayerEnvironment(Protocol):
    line: _RelayerLine


class RelayerFunction:
    """Set the layer on the generated line."""

    name: ClassVar[str] = "relayer"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, layer: int) -> str:
        typed_env = cast(_RelayerEnvironment, env)
        typed_env.line.layer = layer
        return ""
