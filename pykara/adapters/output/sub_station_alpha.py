"""SSA/ASS output adapter backed by pysubs2."""

from __future__ import annotations

from pathlib import Path

from pysubs2 import SSAFile
from pysubs2.common import Alignment, Color
from pysubs2.ssaevent import SSAEvent
from pysubs2.ssastyle import SSAStyle

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Style
from pykara.errors import DocumentWriteError


class SubStationAlphaWriter:
    """Write normalized subtitle documents as ASS/SSA files."""

    def write(self, document: SubtitleDocument, path: str | Path) -> None:
        """Serialize a subtitle document to disk via pysubs2.

        Args:
            document: Normalized subtitle document to serialize.
            path: Destination ASS or SSA file path.

        Raises:
            DocumentWriteError: If pysubs2 fails to save the subtitle file.
        """

        path_obj = Path(path)
        subtitle_file = SSAFile()
        subtitle_file.info = dict(document.metadata.raw)
        subtitle_file.info["PlayResX"] = str(document.metadata.res_x)
        subtitle_file.info["PlayResY"] = str(document.metadata.res_y)
        subtitle_file.styles = {
            name: self._to_style(style)
            for name, style in document.styles.items()
        }
        subtitle_file.events = [
            self._to_event(event) for event in document.events
        ]

        try:
            subtitle_file.save(path_obj)
        except Exception as error:
            raise DocumentWriteError(path_obj, message=str(error)) from error

    def _to_style(self, style: Style) -> SSAStyle:
        """Convert one normalized style into a pysubs2 style."""

        return SSAStyle(
            fontname=style.fontname,
            fontsize=style.fontsize,
            primarycolor=self._to_color(style.primary_colour),
            secondarycolor=self._to_color(style.secondary_colour),
            outlinecolor=self._to_color(style.outline_colour),
            backcolor=self._to_color(style.back_colour),
            bold=style.bold,
            italic=style.italic,
            underline=style.underline,
            strikeout=style.strike_out,
            scalex=style.scale_x,
            scaley=style.scale_y,
            spacing=style.spacing,
            angle=style.angle,
            borderstyle=style.border_style,
            outline=style.outline,
            shadow=style.shadow,
            alignment=Alignment(style.alignment),
            marginl=style.margin_l,
            marginr=style.margin_r,
            marginv=style.margin_t,
            encoding=style.encoding,
        )

    def _to_event(self, event: Event) -> SSAEvent:
        """Convert one normalized event into a pysubs2 event."""

        return SSAEvent(
            start=event.start_time,
            end=event.end_time,
            text=event.text,
            effect=event.effect,
            style=event.style,
            layer=event.layer,
            type="Comment" if event.comment else "Dialogue",
            name=event.actor,
            marginl=event.margin_l,
            marginr=event.margin_r,
            marginv=event.margin_t,
        )

    def _to_color(self, value: str) -> Color:
        """Convert ``&HAABBGGRR`` strings into pysubs2 colors."""

        normalized = value.strip().upper()
        if normalized.startswith("&H"):
            normalized = normalized[2:]
        if normalized.endswith("&"):
            normalized = normalized[:-1]

        payload = normalized.rjust(8, "0")
        return Color(
            r=int(payload[6:8], 16),
            g=int(payload[4:6], 16),
            b=int(payload[2:4], 16),
            a=int(payload[0:2], 16),
        )
