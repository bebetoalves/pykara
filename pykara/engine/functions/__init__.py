"""Public exports for execution namespace functions."""

from pykara.engine.functions._base import Function, FunctionRegistry
from pykara.engine.functions.color import (
    AssAlphaFunction,
    AssColorFunction,
    InterpolateColorFunction,
)
from pykara.engine.functions.geometry import (
    PolarFunction,
    RoundCoordFunction,
    ShapeCenterAtFunction,
    ShapeDisplaceFunction,
    ShapeRotateFunction,
    ShapeSplitClipFunction,
)
from pykara.engine.functions.layer import LayerSetFunction
from pykara.engine.functions.retime import RETIME_MODES, RetimeFunction
from pykara.engine.functions.store import GetFunction, SetFunction

FUNCTION_REGISTRY = FunctionRegistry()
for _function in (
    RetimeFunction(),
    LayerSetFunction(),
    GetFunction(),
    SetFunction(),
    AssColorFunction(),
    AssAlphaFunction(),
    InterpolateColorFunction(),
    PolarFunction(),
    RoundCoordFunction(),
    ShapeRotateFunction(),
    ShapeCenterAtFunction(),
    ShapeDisplaceFunction(),
    ShapeSplitClipFunction(),
):
    FUNCTION_REGISTRY.register(_function)

__all__ = [
    "FUNCTION_REGISTRY",
    "RETIME_MODES",
    "AssAlphaFunction",
    "AssColorFunction",
    "Function",
    "FunctionRegistry",
    "GetFunction",
    "InterpolateColorFunction",
    "LayerSetFunction",
    "PolarFunction",
    "RetimeFunction",
    "RoundCoordFunction",
    "SetFunction",
    "ShapeCenterAtFunction",
    "ShapeDisplaceFunction",
    "ShapeRotateFunction",
    "ShapeSplitClipFunction",
]
