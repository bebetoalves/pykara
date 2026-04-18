"""SSA/ASS input adapter backed by pysubs2."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pysubs2 import SSAFile
from pysubs2.common import Color
from pysubs2.ssaevent import SSAEvent
from pysubs2.ssastyle import SSAStyle

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Metadata, Style
from pykara.errors import DocumentReadError

_DEFAULT_VIDEO_X_CORRECT_FACTOR = 1.0
_DUMMY_VIDEO_WIDTH_INDEX = 3
_DUMMY_VIDEO_HEIGHT_INDEX = 4


class SubStationAlphaReader:
    """Read ASS/SSA documents into the format-agnostic domain model."""

    def read(self, path: str | Path) -> SubtitleDocument:
        """Load an ASS/SSA file from disk.

        Args:
            path: Path to the subtitle file.

        Returns:
            Parsed subtitle document using domain-level data classes.

        Raises:
            DocumentReadError: If the file cannot be parsed by pysubs2.
        """

        path_obj = Path(path)
        try:
            subtitle_file = SSAFile.load(path_obj)
        except Exception as error:
            message = str(error)
            if not message:
                message = f"Could not parse subtitle document: {path_obj}"
            raise DocumentReadError(path_obj, message=message) from error

        return SubtitleDocument(
            metadata=self._to_metadata(
                info=subtitle_file.info,
                project=subtitle_file.aegisub_project,
            ),
            styles={
                name: self._to_style(name=name, raw=raw_style)
                for name, raw_style in subtitle_file.styles.items()
            },
            events=[
                self._to_event(raw_event) for raw_event in subtitle_file.events
            ],
        )

    def _to_metadata(
        self,
        info: Mapping[str, str],
        project: Mapping[str, str] | None = None,
    ) -> Metadata:
        """Convert script metadata from pysubs2 into the domain model."""

        res_x = self._parse_int(info.get("PlayResX"))
        res_y = self._parse_int(info.get("PlayResY"))
        raw = dict(info)
        if project is not None:
            raw.update(project)

        return Metadata(
            res_x=res_x,
            res_y=res_y,
            video_x_correct_factor=self._to_video_x_correct_factor(
                res_x=res_x,
                res_y=res_y,
                project=project,
            ),
            raw=raw,
        )

    def _to_style(self, name: str, raw: SSAStyle) -> Style:
        """Convert a pysubs2 style into the normalized style model."""

        return Style(
            name=name,
            fontname=raw.fontname,
            fontsize=raw.fontsize,
            primary_colour=self._to_ass_color(raw.primarycolor),
            secondary_colour=self._to_ass_color(raw.secondarycolor),
            outline_colour=self._to_ass_color(raw.outlinecolor),
            back_colour=self._to_ass_color(raw.backcolor),
            bold=raw.bold,
            italic=raw.italic,
            underline=raw.underline,
            strike_out=raw.strikeout,
            scale_x=raw.scalex,
            scale_y=raw.scaley,
            spacing=raw.spacing,
            angle=raw.angle,
            border_style=raw.borderstyle,
            outline=raw.outline,
            shadow=raw.shadow,
            alignment=int(raw.alignment),
            margin_l=raw.marginl,
            margin_r=raw.marginr,
            margin_t=raw.marginv,
            margin_b=raw.marginv,
            encoding=raw.encoding,
        )

    def _to_event(self, raw: SSAEvent) -> Event:
        """Convert a pysubs2 event into the normalized event model."""

        return Event(
            text=raw.text,
            effect=raw.effect,
            style=raw.style,
            layer=raw.layer,
            start_time=raw.start,
            end_time=raw.end,
            comment=raw.is_comment,
            actor=raw.name,
            margin_l=raw.marginl,
            margin_r=raw.marginr,
            margin_t=raw.marginv,
            margin_b=raw.marginv,
        )

    def _to_video_x_correct_factor(
        self,
        *,
        res_x: int,
        res_y: int,
        project: Mapping[str, str] | None,
    ) -> float:
        """Compute the same X correction factor used by karaskel."""

        if project is None or res_x <= 0 or res_y <= 0:
            return _DEFAULT_VIDEO_X_CORRECT_FACTOR

        video_resolution = self._parse_dummy_video_resolution(project)
        if video_resolution is not None:
            video_x, video_y = video_resolution
            if video_x > 0 and video_y > 0:
                return (video_y / video_x) / (res_y / res_x)

        aspect_ratio = self._parse_float(project.get("Video AR Value"))
        if aspect_ratio is None or aspect_ratio <= 0:
            return _DEFAULT_VIDEO_X_CORRECT_FACTOR

        return (1.0 / aspect_ratio) / (res_y / res_x)

    def _parse_dummy_video_resolution(
        self, project: Mapping[str, str]
    ) -> tuple[int, int] | None:
        """Extract dummy-video dimensions from Aegisub project metadata."""

        video_file = project.get("Video File")
        if video_file is None or not video_file.startswith("?dummy:"):
            return None

        tokens = video_file.split(":")
        if len(tokens) <= _DUMMY_VIDEO_HEIGHT_INDEX:
            return None

        width = self._parse_int(tokens[_DUMMY_VIDEO_WIDTH_INDEX])
        height = self._parse_int(tokens[_DUMMY_VIDEO_HEIGHT_INDEX])
        if width <= 0 or height <= 0:
            return None

        return width, height

    def _parse_int(self, value: str | None) -> int:
        """Safely parse integer metadata values."""

        if value is None:
            return 0

        try:
            return int(value)
        except ValueError:
            return 0

    def _parse_float(self, value: str | None) -> float | None:
        """Safely parse floating-point metadata values."""

        if value is None:
            return None

        try:
            return float(value)
        except ValueError:
            return None

    def _to_ass_color(self, color: Color) -> str:
        """Convert a pysubs2 color to ASS ``&HAABBGGRR`` notation."""

        return f"&H{color.a:02X}{color.b:02X}{color.g:02X}{color.r:02X}"
