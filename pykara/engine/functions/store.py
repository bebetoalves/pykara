"""Shared key-value store functions."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import ClassVar, Protocol, cast

from pykara.errors import BoundMethodInExpressionError


class _StoreEnvironment(Protocol):
    store: MutableMapping[str, object]


class GetFunction:
    """Read one value from the shared store."""

    name: ClassVar[str] = "get"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        key: str,
        default_value: object = None,
    ) -> object:
        typed_env = cast(_StoreEnvironment, env)
        return typed_env.store.get(key, default_value)


class SetFunction:
    """Write one value into the shared store."""

    name: ClassVar[str] = "set"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, key: str, value: object) -> object:
        if callable(value):
            raise BoundMethodInExpressionError(
                expression=f'set("{key}", ...)',
                result_type=type(value).__name__,
            )
        typed_env = cast(_StoreEnvironment, env)
        typed_env.store[key] = value
        return value
