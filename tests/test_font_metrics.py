"""Tests for font measurement utilities."""

# pyright: reportUnknownMemberType=false, reportPrivateUsage=false

from __future__ import annotations

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pykara.data import Style
from pykara.errors import DependencyUnavailableError, PykaraError
from pykara.processing import font_metrics
from pykara.processing.font_metrics import (
    FontMetricsProvider,
    TextExtentsProvider,
    _load_backend,
    _resolve_font_path,
    _shape_width,
    get_gdi_metrics,
    reset_font_cache,
)


def make_style(
    *,
    fontname: str = "Noto Sans",
    fontsize: float = 24.0,
    scale_x: float = 100.0,
    scale_y: float = 100.0,
    spacing: float = 0.0,
) -> Style:
    return Style(
        name="Default",
        fontname=fontname,
        fontsize=fontsize,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H000000FF",
        outline_colour="&H00000000",
        back_colour="&H00000000",
        bold=False,
        italic=False,
        underline=False,
        strike_out=False,
        scale_x=scale_x,
        scale_y=scale_y,
        spacing=spacing,
        angle=0.0,
        border_style=1,
        outline=2.0,
        shadow=0.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=10,
        margin_b=10,
        encoding=1,
    )


class TestFontMetricsProvider:
    def test_satisfies_text_extents_protocol(self) -> None:
        provider: TextExtentsProvider = FontMetricsProvider()

        measurement = provider.measure(make_style(), "Hi")

        assert measurement.width > 0

    def test_measures_known_reference_text(self) -> None:
        provider = FontMetricsProvider()
        measurement = provider.measure(make_style(), "Hello")

        assert measurement.width == pytest.approx(
            42.7488986784141,
            abs=0.0001,
        )
        assert measurement.height == pytest.approx(24.0, abs=0.0001)
        assert measurement.descent == pytest.approx(
            5.1629955947136565,
            abs=0.0001,
        )
        assert measurement.extlead == pytest.approx(0.0, abs=0.0001)

    def test_spacing_increases_width(self) -> None:
        provider = FontMetricsProvider()
        compact = provider.measure(make_style(spacing=0.0), "Hello")
        spaced = provider.measure(make_style(spacing=2.0), "Hello")

        assert spaced.width > compact.width

    def test_scale_x_and_scale_y_affect_output_axes(self) -> None:
        provider = FontMetricsProvider()
        base = provider.measure(make_style(scale_x=100.0, scale_y=100.0), "Hi")
        scaled = provider.measure(
            make_style(scale_x=150.0, scale_y=200.0),
            "Hi",
        )

        assert scaled.width == pytest.approx(base.width * 1.5, abs=0.0001)
        assert scaled.height == pytest.approx(base.height * 2.0, abs=0.0001)
        assert scaled.descent == pytest.approx(base.descent * 2.0, abs=0.0001)

    def test_reuses_cached_measurements_for_same_style_and_text(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reset_font_cache()
        provider = FontMetricsProvider()
        raw_calls = 0

        def fake_measure_raw_text(
            style: Style,
            text: str,
            font_dirs: tuple[object, ...] = (),
        ) -> tuple[float, float, float, float]:
            del style, text, font_dirs
            nonlocal raw_calls
            raw_calls += 1
            return (64.0, 64.0, 16.0, 0.0)

        monkeypatch.setattr(
            font_metrics,
            "_measure_raw_text",
            fake_measure_raw_text,
        )

        first = provider.measure(make_style(), "cached")
        second = provider.measure(make_style(), "cached")

        assert first == second
        assert raw_calls == 1


class TestShapeWidth:
    def test_returns_zero_for_empty_string(self) -> None:
        assert _shape_width(hb_font=None, text="") == 0.0


class TestResetFontCache:
    def test_resets_backend_and_metrics_caches(self) -> None:
        provider = FontMetricsProvider()
        provider.measure(make_style(), "primed")

        assert (
            font_metrics._FONT_CACHE
            or font_metrics._FONT_METRICS_CACHE
            or font_metrics._MEASUREMENT_CACHE
        )

        reset_font_cache()

        assert not font_metrics._FONT_CACHE
        assert not font_metrics._FONT_METRICS_CACHE
        assert not font_metrics._MEASUREMENT_CACHE


class TestResolveFontPath:
    def test_raises_pykara_error_for_unknown_font(self) -> None:
        with pytest.raises(PykaraError, match="unknown font family"):
            _resolve_font_path(
                "this-font-does-not-exist-1234",
                is_bold=False,
                is_italic=False,
            )


class TestGetGdiMetrics:
    def test_returns_cached_metrics_on_second_call(self) -> None:
        reset_font_cache()
        provider = FontMetricsProvider()
        provider.measure(make_style(), "cached")

        cached_paths = list(font_metrics._FONT_METRICS_CACHE)
        assert cached_paths, "expected at least one cached font path"
        font_path = cached_paths[0]
        cached = font_metrics._FONT_METRICS_CACHE[font_path]

        assert get_gdi_metrics(font_path, ft_face=None) == cached

    def test_falls_back_to_freetype_when_tt_font_raises(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reset_font_cache()
        provider = FontMetricsProvider()
        provider.measure(make_style(), "warm")
        cached_paths = list(font_metrics._FONT_METRICS_CACHE)
        assert cached_paths
        font_path = cached_paths[0]

        font_cache_key = next(iter(font_metrics._FONT_CACHE))
        ft_face = font_metrics._FONT_CACHE[font_cache_key][0]

        font_metrics._FONT_METRICS_CACHE.pop(font_path, None)

        def raising_ttfont(*_args: object, **_kwargs: object) -> None:
            raise OSError("simulated TTFont failure")

        monkeypatch.setattr(font_metrics, "TTFont", raising_ttfont)

        metrics = get_gdi_metrics(font_path, ft_face)

        assert metrics[0] > 0
        assert metrics[2] > 0
        reset_font_cache()

    def test_raises_when_tt_font_type_is_missing(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reset_font_cache()
        provider = FontMetricsProvider()
        provider.measure(make_style(), "warm")
        cached_paths = list(font_metrics._FONT_METRICS_CACHE)
        font_path = cached_paths[0]
        font_metrics._FONT_METRICS_CACHE.pop(font_path, None)

        monkeypatch.setattr(font_metrics, "TTFont", None)

        with pytest.raises(DependencyUnavailableError, match="TTFont"):
            get_gdi_metrics(font_path, ft_face=None)
        reset_font_cache()


class TestRequireDependencies:
    def test_raises_dependency_unavailable_when_imports_failed(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            font_metrics,
            "IMPORT_ERROR",
            ImportError("missing optional dependencies"),
        )

        with pytest.raises(DependencyUnavailableError):
            font_metrics._require_dependencies()

    def test_freetype_getter_raises_when_module_is_none(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_metrics, "IMPORT_ERROR", None)
        monkeypatch.setattr(font_metrics, "freetype", None)

        with pytest.raises(DependencyUnavailableError, match="freetype"):
            font_metrics._get_freetype_module()

    def test_harfbuzz_getter_raises_when_module_is_none(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(font_metrics, "IMPORT_ERROR", None)
        monkeypatch.setattr(font_metrics, "hb", None)

        with pytest.raises(DependencyUnavailableError, match="uharfbuzz"):
            font_metrics._get_harfbuzz_module()


class TestLoadBackend:
    def test_returns_backend_module_on_success(self) -> None:
        _load_backend.cache_clear()

        backend = _load_backend()

        assert backend is font_metrics
        _load_backend.cache_clear()

    def test_raises_when_backend_reports_import_error(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        _load_backend.cache_clear()
        monkeypatch.setattr(
            font_metrics,
            "IMPORT_ERROR",
            ImportError("backend missing"),
        )

        with pytest.raises(PykaraError, match="missing dependencies"):
            _load_backend()

        _load_backend.cache_clear()
