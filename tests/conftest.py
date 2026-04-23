"""Shared test setup."""

# pyright: reportPrivateUsage=false, reportUnknownMemberType=false

from __future__ import annotations

import os
from pathlib import Path

import pytest
from matplotlib import font_manager

from pykara.processing import font_metrics
from pykara.processing.font_metrics import reset_font_cache

_FONT_PATH = (
    Path(__file__).parent / "fixtures" / "fonts" / "NotoSans-Regular.ttf"
)


@pytest.fixture(scope="session", autouse=True)
def register_test_fonts(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Register bundled fonts and isolate matplotlib cache writes."""

    os.environ.setdefault(
        "MPLCONFIGDIR",
        str(tmp_path_factory.mktemp("mplconfig")),
    )
    font_manager.fontManager.addfont(str(_FONT_PATH.resolve()))
    font_metrics._register_font_dirs_win32((_FONT_PATH.parent,))
    reset_font_cache()
