"""High-fidelity document parser using the Unstructured library.

Uses ``partition_pdf`` (hi_res mode) and ``partition_docx`` to
extract semantic elements — Title, NarrativeText, Table, ListItem —
with full page-number and element-type metadata.  Ideal for scanned
PDFs, complex layouts, and documents where PyMuPDF alone loses
structure.

This parser is **optional**: the factory only invokes it when
``unstructured`` is installed.  If the import fails the factory
silently falls back to the lightweight parsers.

Usage::

    from app.core.parsers.unstructured_parser import UnstructuredParser

    parser = UnstructuredParser()
    if parser.supports(Path("scan.pdf")):
        doc = parser.parse(Path("scan.pdf"))
"""

import logging
from pathlib import Path

from app.core.parsers.base import (
    BaseParser,
    ParsedDocument,
    ParsedPage,
    ParserError,
)

logger = logging.getLogger(__name__)

# Map Unstructured element class names to our element_type strings.
_ELEMENT_TYPE_MAP: dict[str, str] = {
    "Title": "Title",
    "NarrativeText": "NarrativeText",
    "Table": "Table",
    "ListItem": "ListItem",
    "UncategorizedText": "NarrativeText",
    "Header": "Title",
    "Footer": "NarrativeText",
    "PageBreak": "NarrativeText",
    "Image": "NarrativeText",
    "FigureCaption": "NarrativeText",
    "Address": "NarrativeText",
    "EmailAddress": "NarrativeText",
    "Formula": "NarrativeText",
}


class UnstructuredParser(BaseParser):
    """Parser backed by the Unstructured library.

    Supports PDF (hi_res strategy) and DOCX.  Falls back gracefully
    when optional OCR dependencies (tesseract, poppler) are missing
    by using the ``fast`` strategy.
    """

    def supported_extensions(self) -> list[str]:
        """Return supported extensions.

        Returns:
            List containing ``".pdf"`` and ``".docx"``.
        """
        return [".pdf", ".docx"]

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a document using Unstructured.

        Automatically selects ``partition_pdf`` or ``partition_docx``
        based on the file extension.

        Args:
            file_path: Absolute path to the document.

        Returns:
            Parsed document with semantic element metadata.

        Raises:
            ParserError: If ``unstructured`` is not installed or
                parsing fails.
        """
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            return self._parse_pdf(file_path)
        elif ext in (".docx", ".doc"):
            return self._parse_docx(file_path)
        else:
            raise ParserError(
                detail=f"UnstructuredParser does not support '{ext}'",
                file_path=str(file_path),
            )

    # ── PDF ───────────────────────────────────────────────────

    def _parse_pdf(self, file_path: Path) -> ParsedDocument:
        """Parse a PDF with ``partition_pdf`` (hi_res → fast fallback).

        Args:
            file_path: Path to the PDF.

        Returns:
            Parsed document.
        """
        try:
            from unstructured.partition.pdf import partition_pdf
        except ImportError as exc:
            raise ParserError(
                detail="unstructured[pdf] is not installed",
                file_path=str(file_path),
            ) from exc

        elements = self._partition_with_fallback(
            partition_pdf, str(file_path)
        )
        return self._build_document(elements, file_path)

    # ── DOCX ──────────────────────────────────────────────────

    def _parse_docx(self, file_path: Path) -> ParsedDocument:
        """Parse a DOCX with ``partition_docx``.

        Args:
            file_path: Path to the DOCX.

        Returns:
            Parsed document.
        """
        try:
            from unstructured.partition.docx import partition_docx
        except ImportError as exc:
            raise ParserError(
                detail="unstructured[docx] is not installed",
                file_path=str(file_path),
            ) from exc

        try:
            elements = partition_docx(filename=str(file_path))
        except Exception as exc:
            raise ParserError(
                detail=f"Unstructured DOCX parsing failed: {exc}",
                file_path=str(file_path),
            ) from exc

        return self._build_document(elements, file_path)

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _partition_with_fallback(
        partition_fn: object, file_path: str
    ) -> list:
        """Try hi_res strategy first, fall back to fast.

        The ``hi_res`` strategy uses layout detection + OCR and
        produces the best results for scanned PDFs, but requires
        extra system dependencies (tesseract, poppler).  When those
        are missing we fall back to the ``fast`` strategy which
        only needs PyMuPDF.

        Args:
            partition_fn: The ``partition_pdf`` callable.
            file_path: Path to the PDF file.

        Returns:
            List of Unstructured elements.
        """
        # Try hi_res first
        try:
            elements = partition_fn(
                filename=file_path,
                strategy="hi_res",
                include_page_metadata=True,
            )
            logger.debug("PDF parsed with hi_res strategy: %s", file_path)
            return elements
        except Exception as exc:
            logger.info(
                "hi_res strategy failed (%s), falling back to fast: %s",
                type(exc).__name__, file_path,
            )

        # Fallback to fast
        try:
            elements = partition_fn(
                filename=file_path,
                strategy="fast",
                include_page_metadata=True,
            )
            logger.debug("PDF parsed with fast strategy: %s", file_path)
            return elements
        except Exception as exc:
            raise ParserError(
                detail=f"All PDF parsing strategies failed: {exc}",
                file_path=file_path,
            ) from exc

    def _build_document(
        self, elements: list, file_path: Path
    ) -> ParsedDocument:
        """Convert Unstructured elements into a ``ParsedDocument``.

        Each element becomes a :class:`ParsedPage` with
        ``element_type`` and ``source`` populated.

        Args:
            elements: List of Unstructured element objects.
            file_path: Source file path (for metadata).

        Returns:
            Unified parsed document.
        """
        pages: list[ParsedPage] = []
        full_text_parts: list[str] = []
        title = ""
        source_name = file_path.name

        for element in elements:
            # Extract text content
            text = str(element).strip()
            if not text:
                continue

            # Determine element type
            element_class = type(element).__name__
            element_type = _ELEMENT_TYPE_MAP.get(element_class, "NarrativeText")

            # Extract page number from metadata
            page_number: int | None = None
            metadata = getattr(element, "metadata", None)
            if metadata is not None:
                page_meta = getattr(metadata, "page_number", None)
                if page_meta is not None:
                    page_number = int(page_meta)

            # First Title element becomes the document title
            if element_type == "Title" and not title:
                title = text

            pages.append(
                ParsedPage(
                    page_number=page_number,
                    content=text,
                    heading=text if element_type == "Title" else None,
                    heading_level=1 if element_type == "Title" else None,
                    element_type=element_type,
                    source=source_name,
                )
            )
            full_text_parts.append(text)

        if not title:
            title = file_path.stem

        full_text = "\n\n".join(full_text_parts)

        # Build stats for logging
        type_counts: dict[str, int] = {}
        for p in pages:
            type_counts[p.element_type] = type_counts.get(p.element_type, 0) + 1

        logger.debug(
            "Unstructured parsed %s: %d elements (%s), %d chars",
            source_name, len(pages), type_counts, len(full_text),
        )

        return ParsedDocument(
            title=title,
            pages=pages,
            full_text=full_text,
            metadata={"source": source_name, "element_counts": type_counts},
        )
