"""PDF parser factory with automatic classification.

Combines the :class:`~app.core.parsers.pdf_classifier.PDFClassifier`
with the four specialized PDF parsers to provide a single
``parse_file()`` entry point that "just works" for any PDF.

Usage::

    from app.core.parsers.parser_factory import ParserFactory

    doc = ParserFactory.parse_file(Path("any_document.pdf"))
    print(doc.metadata["type"])   # "native" / "scanned" / "hybrid" / "complex"
    print(doc.metadata["parser"]) # "NativePDFParser" / ...
"""

import logging
from pathlib import Path

from app.core.parsers.base import (
    ParsedDocument,
    ParserError,
    PDFType,
)
from app.core.parsers.pdf_classifier import PDFClassifier

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory that classifies a PDF and dispatches to the right parser.

    The classifier runs first (fast, < 100 ms), then the appropriate
    parser is invoked.  If a specialized parser fails, the factory
    falls back to lighter alternatives.
    """

    _classifier = PDFClassifier()

    @classmethod
    def get_parser(cls, pdf_type: PDFType):
        """Return the parser instance for a given PDF type.

        Args:
            pdf_type: Classified PDF type.

        Returns:
            Parser instance.

        Raises:
            ParserError: If the required parser dependencies are missing.
        """
        from app.core.parsers.pdf.native_parser import NativePDFParser
        from app.core.parsers.pdf.scanned_parser import ScannedPDFParser
        from app.core.parsers.pdf.hybrid_parser import HybridPDFParser
        from app.core.parsers.pdf.complex_parser import ComplexPDFParser

        _PARSER_MAP = {
            PDFType.NATIVE: NativePDFParser,
            PDFType.SCANNED: ScannedPDFParser,
            PDFType.HYBRID: HybridPDFParser,
            PDFType.COMPLEX: ComplexPDFParser,
        }

        parser_cls = _PARSER_MAP.get(pdf_type)
        if parser_cls is None:
            raise ParserError(
                detail=f"No parser for PDF type '{pdf_type}'",
            )

        return parser_cls()

    @classmethod
    def parse_file(
        cls,
        file_path: Path,
        *,
        pdf_type: PDFType | None = None,
    ) -> ParsedDocument:
        """Classify and parse a PDF file.

        If *pdf_type* is provided the classification step is skipped.
        Otherwise the classifier examines the PDF structure and
        selects the best parser automatically.

        Fallback chain:
        * ComplexPDFParser fails → HybridPDFParser
        * HybridPDFParser fails → NativePDFParser
        * ScannedPDFParser fails → UnstructuredParser (if installed)
        * All fail → ParserError

        Args:
            file_path: Absolute path to the PDF.
            pdf_type: Optional explicit type (skips classification).

        Returns:
            Parsed document.

        Raises:
            ParserError: If all parsers fail.
        """
        if not file_path.exists():
            raise ParserError(
                detail=f"File not found: {file_path}",
                file_path=str(file_path),
            )

        # Classify
        if pdf_type is None:
            pdf_type, page_details = cls._classifier.classify(file_path)
            logger.info(
                "PDF %s classified as %s (%d pages)",
                file_path.name, pdf_type.value, len(page_details),
            )

        # Parse with fallback
        return cls._parse_with_fallback(file_path, pdf_type)

    @classmethod
    def _parse_with_fallback(
        cls, file_path: Path, pdf_type: PDFType
    ) -> ParsedDocument:
        """Parse with the best parser, falling back on failure.

        Args:
            file_path: Path to the PDF.
            pdf_type: Classified type.

        Returns:
            Parsed document.

        Raises:
            ParserError: If all attempts fail.
        """
        errors: list[str] = []

        # Primary parser
        try:
            parser = cls.get_parser(pdf_type)
            doc = parser.parse(file_path)
            doc.metadata["type"] = pdf_type.value
            return doc
        except Exception as exc:
            errors.append(f"{pdf_type.value}: {exc}")
            logger.warning(
                "Primary parser (%s) failed for %s: %s",
                pdf_type.value, file_path.name, exc,
            )

        # Fallback chain
        fallback_order = cls._get_fallback_chain(pdf_type)
        for fallback_type in fallback_order:
            try:
                parser = cls.get_parser(fallback_type)
                doc = parser.parse(file_path)
                doc.metadata["type"] = fallback_type.value
                doc.metadata["fallback_from"] = pdf_type.value
                logger.info(
                    "Fallback parser (%s) succeeded for %s",
                    fallback_type.value, file_path.name,
                )
                return doc
            except Exception as exc:
                errors.append(f"{fallback_type.value}: {exc}")
                logger.warning(
                    "Fallback parser (%s) failed for %s: %s",
                    fallback_type.value, file_path.name, exc,
                )

        # Last resort: UnstructuredParser
        try:
            from app.core.parsers.unstructured_parser import UnstructuredParser
            us = UnstructuredParser()
            doc = us.parse(file_path)
            doc.metadata["type"] = pdf_type.value
            doc.metadata["fallback_from"] = "all_failed"
            logger.info(
                "UnstructuredParser (last resort) succeeded for %s",
                file_path.name,
            )
            return doc
        except Exception as exc:
            errors.append(f"unstructured: {exc}")

        raise ParserError(
            detail=f"All parsers failed for {file_path.name}: {'; '.join(errors)}",
            file_path=str(file_path),
        )

    @staticmethod
    def _get_fallback_chain(pdf_type: PDFType) -> list[PDFType]:
        """Return the fallback order for a given PDF type.

        Args:
            pdf_type: Primary type that failed.

        Returns:
            List of types to try in order.
        """
        chains: dict[PDFType, list[PDFType]] = {
            PDFType.COMPLEX: [PDFType.HYBRID, PDFType.NATIVE],
            PDFType.HYBRID: [PDFType.NATIVE],
            PDFType.SCANNED: [PDFType.HYBRID],
            PDFType.NATIVE: [PDFType.HYBRID],
        }
        return chains.get(pdf_type, [PDFType.NATIVE])
