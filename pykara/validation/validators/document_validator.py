"""Top-level validator that orchestrates all validation stages."""

from __future__ import annotations

import re

from pykara.adapters import SubtitleDocument
from pykara.data import Event
from pykara.parsing import (
    CodeDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.parsing.karaoke_parser import KaraokeParser
from pykara.validation.reports import ValidationReport
from pykara.validation.validators.code_validator import CodeValidator
from pykara.validation.validators.cross_validator import CrossValidator
from pykara.validation.validators.event_validator import EventValidator
from pykara.validation.validators.karaoke_validator import KaraokeValidator
from pykara.validation.validators.metadata_validator import MetadataValidator
from pykara.validation.validators.patch_validator import PatchValidator
from pykara.validation.validators.style_validator import StyleValidator
from pykara.validation.validators.template_validator import TemplateValidator

_KARAOKE_TAG_PATTERN = re.compile(r"\\(?:k|K|kf)\d+")


class DocumentValidator:
    """Run all domain and cross validators for one document."""

    def __init__(self) -> None:
        self._metadata_validator = MetadataValidator()
        self._style_validator = StyleValidator()
        self._event_validator = EventValidator()
        self._karaoke_parser = KaraokeParser()
        self._karaoke_validator = KaraokeValidator()
        self._template_validator = TemplateValidator()
        self._patch_validator = PatchValidator()
        self._code_validator = CodeValidator()
        self._cross_validator = CrossValidator()

    def validate(
        self,
        document: SubtitleDocument,
        declarations: ParsedDeclarations,
    ) -> ValidationReport:
        """Validate one document together with its parsed declarations.

        Args:
            document: Loaded subtitle document.
            declarations: Parsed declarations for that document.

        Returns:
            Aggregated validation report.
        """
        report = self._metadata_validator.validate(document.metadata)

        for style in document.styles.values():
            report = report.merge(self._style_validator.validate(style))

        for event in document.events:
            report = report.merge(self._event_validator.validate(event))
            report = report.merge(self._validate_event_karaoke(event))

        for declaration in declarations.line:
            report = report.merge(
                self._validate_scoped_declaration(declaration)
            )

        for declaration in declarations.syl:
            report = report.merge(
                self._validate_scoped_declaration(declaration)
            )

        for declaration in declarations.char:
            report = report.merge(
                self._template_validator.validate(declaration)
            )

        for declaration in declarations.patch_line:
            report = report.merge(self._patch_validator.validate(declaration))

        for declaration in declarations.patch_word:
            report = report.merge(self._patch_validator.validate(declaration))

        for declaration in declarations.patch_syl:
            report = report.merge(self._patch_validator.validate(declaration))

        for declaration in declarations.patch_char:
            report = report.merge(self._patch_validator.validate(declaration))

        for declaration in declarations.setup:
            report = report.merge(self._code_validator.validate(declaration))

        return report.merge(
            self._cross_validator.validate(document, declarations)
        )

    def _validate_event_karaoke(self, event: Event) -> ValidationReport:
        if event.comment or _KARAOKE_TAG_PATTERN.search(event.text) is None:
            return ValidationReport()

        karaoke = self._karaoke_parser.parse(event)
        report = ValidationReport()
        for syllable in karaoke.syllables:
            report = report.merge(self._karaoke_validator.validate(syllable))
        return report

    def _validate_scoped_declaration(
        self,
        declaration: TemplateDeclaration | CodeDeclaration,
    ) -> ValidationReport:
        if isinstance(declaration, TemplateDeclaration):
            return self._template_validator.validate(declaration)
        return self._code_validator.validate(declaration)
