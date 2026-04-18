"""Validation rules for parsed karaoke syllables."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data import Syllable
from pykara.validation.reports import Severity, Violation


@dataclass(frozen=True, slots=True)
class PositiveSyllableDurationRule:
    """Ensure syllable timing is strictly positive."""

    code: str = "karaoke.duration_positive"
    severity: Severity = Severity.ERROR

    def check(self, subject: Syllable) -> Violation | None:
        if subject.duration > 0:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Syllable duration must be positive.",
            context=f"index={subject.index}, duration={subject.duration}",
            location="syllable.duration",
        )


@dataclass(frozen=True, slots=True)
class TimedSyllableTextRule:
    """Ensure timed syllables carry visible text after stripping spaces."""

    code: str = "karaoke.timed_text_required"
    severity: Severity = Severity.ERROR

    def check(self, subject: Syllable) -> Violation | None:
        if subject.duration <= 0 or subject.trimmed_text:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Timed syllables must contain non-whitespace text.",
            context=f"index={subject.index}, text={subject.text!r}",
            location="syllable.text",
        )
