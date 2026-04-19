"""Public exports for patch declarations."""

from pykara.declaration._shared import ModifierRegistry
from pykara.declaration.patch.body import PatchBody
from pykara.declaration.patch.modifiers import (
    ForModifier,
    LayerModifier,
    PatchFxModifier,
    PatchModifiers,
    PatchUnlessModifier,
    PatchWhenModifier,
    PrependModifier,
)

PATCH_MODIFIER_REGISTRY: ModifierRegistry[PatchModifiers] = ModifierRegistry(
    default=PatchModifiers()
)

for _handler in (
    PrependModifier(),
    LayerModifier(),
    ForModifier(),
    PatchFxModifier(),
    PatchWhenModifier(),
    PatchUnlessModifier(),
):
    PATCH_MODIFIER_REGISTRY.register(_handler)

__all__ = [
    "PATCH_MODIFIER_REGISTRY",
    "ForModifier",
    "LayerModifier",
    "PatchBody",
    "PatchFxModifier",
    "PatchModifiers",
    "PatchUnlessModifier",
    "PatchWhenModifier",
    "PrependModifier",
]
