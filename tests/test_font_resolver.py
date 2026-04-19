"""Tests for platform-aware font resolution."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pykara.errors import PykaraError
from pykara.processing import font_resolver
from pykara.processing.font_resolver import (
    _resolve_with_fontconfig,
    resolve_font,
)

_FONT_PATH = (
    Path(__file__).parent / "fixtures" / "fonts" / "NotoSans-Regular.ttf"
)


class TestResolveFont:
    def test_prefers_explicit_font_dirs(self, tmp_path: Path) -> None:
        font_dir = tmp_path / "fonts"
        font_dir.mkdir()
        font_path = font_dir / "NotoSans-Regular.ttf"
        font_path.write_bytes(_FONT_PATH.read_bytes())

        resolved = resolve_font(
            "Noto Sans",
            is_bold=False,
            is_italic=False,
            font_dirs=(font_dir,),
        )

        assert resolved.path == str(font_path)
        assert resolved.source == "explicit"

    def test_raises_diagnostic_error_for_unknown_font(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        def missing_resolver(*_args: object, **_kwargs: object) -> None:
            return None

        monkeypatch.setattr(font_resolver, "platform", "linux")
        monkeypatch.setattr(
            font_resolver,
            "_resolve_with_fontconfig",
            missing_resolver,
        )
        monkeypatch.setattr(
            font_resolver,
            "_resolve_with_matplotlib",
            missing_resolver,
        )
        monkeypatch.setattr(
            font_resolver,
            "default_user_font_dirs",
            lambda: (Path("/missing/user/fonts"),),
        )
        monkeypatch.setattr(
            font_resolver,
            "default_system_font_dirs",
            lambda: (Path("/missing/system/fonts"),),
        )

        with pytest.raises(PykaraError, match="Tried: fontconfig"):
            resolve_font(
                "this-font-does-not-exist-1234",
                is_bold=False,
                is_italic=False,
            )


class TestFontconfig:
    @staticmethod
    def find_fc_match(_name: str) -> str:
        return "fc-match"

    def test_accepts_matching_fontconfig_family(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        def fake_run(*_args: object, **_kwargs: object) -> object:
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Cookies\t/home/user/.fonts/Cookies.ttf\n",
                stderr="",
            )

        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            self.find_fc_match,
        )
        monkeypatch.setattr(font_resolver.subprocess, "run", fake_run)

        resolved = _resolve_with_fontconfig(
            "Cookies",
            is_bold=False,
            is_italic=False,
        )

        assert resolved is not None
        assert resolved.path == "/home/user/.fonts/Cookies.ttf"
        assert resolved.source == "fontconfig"

    def test_rejects_fontconfig_default_for_unknown_font(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        def fake_run(*_args: object, **_kwargs: object) -> object:
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="Noto Sans\t/usr/share/fonts/NotoSans-Regular.ttf\n",
                stderr="",
            )

        monkeypatch.setattr(
            font_resolver.shutil,
            "which",
            self.find_fc_match,
        )
        monkeypatch.setattr(font_resolver.subprocess, "run", fake_run)

        assert (
            _resolve_with_fontconfig(
                "this-font-does-not-exist-1234",
                is_bold=False,
                is_italic=False,
            )
            is None
        )
