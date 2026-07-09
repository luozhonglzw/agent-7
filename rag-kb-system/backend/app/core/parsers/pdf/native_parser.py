"""Native PDF parser using PyMuPDF direct text extraction.

Optimized for digitally-created PDFs where a text layer is already
present.  Extracts text blocks page-by-page and infers heading
hierarchy from relative font sizes.

Usage::

    from app.core.parsers.pdf.native_parser import NativePDFParser

    parser = NativePDFParser()
    doc = parser.parse(Path("digital_report.pdf"))
"""

import logging
from pathlib import Path

from app.core.parsers.base import (
    ParsedDocument,
    ParsedPage,
    ParsedSection,
    ParserError,
    PDFType,
)

logger = logging.getLogger(__name__)


class NativePDFParser:
    """Extract text directly from digital PDFs via PyMuPDF.

    This parser is the fastest option and should be used whenever
    the PDF contains a real text layer (i.e. not a scanned image).
    """

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a native PDF.

        Args:
            file_path: Path to the PDF.

        Returns:
            Parsed document with sections and metadata.

        Raises:
            ParserError: If PyMuPDF cannot open the file.
        """
        try:
            import fitz
        except ImportError as exc:
            raise ParserError(
                detail="PyMuPDF is not installed",
                file_path=str(file_path),
            ) from exc

        try:
            doc = fitz.open(str(file_path))
        except Exception as exc:
            raise ParserError(
                detail=f"Cannot open PDF: {exc}",
                file_path=str(file_path),
            ) from exc

        pages: list[ParsedPage] = []
        sections: list[ParsedSection] = []
        full_text_parts: list[str] = []
        title = ""

        try:
            meta = doc.metadata or {}
            title = meta.get("title", "") or ""

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                blocks = page.get_text(
                    "dict", flags=fitz.TEXT_PRESERVE_WHITESPACE
                )["blocks"]

                page_parts: list[str] = []
                max_font_size = 0.0
                heading_text = ""

                for block in blocks:
                    if block.get("type") != 0:
                        continue

                    bbox = block.get("bbox", (0, 0, 0, 0))

                    for line in block.get("lines", []):
                        line_parts: list[str] = []
                        line_max_font = 0.0

                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                            line_parts.append(text)
                            font_size = span.get("size", 0)
                            if font_size > line_max_font:
                                line_max_font = font_size

                        if line_parts:
                            line_text = " ".join(line_parts)
                            page_parts.append(line_text)

                            # Track largest font for heading detection
                            if line_max_font > max_font_size:
                                max_font_size = line_max_font
                                if page_num == 0 and not heading_text:
                                    heading_text = line_text

                            # Determine if this is a heading
                            is_heading = line_max_font > max_font_size * 0.8 and (
                                line_max_font > 14
                            )

                            sections.append(
                                ParsedSection(
                                    type="Title" if is_heading else "NarrativeText",
                                    level=1 if is_heading and page_num == 0 else 0,
                                    text=line_text,
                                    page=page_num + 1,
                                    bbox=list(bbox),
                                    confidence=1.0,
                                )
                            )

                page_text = " ".join(page_parts)
                if page_text.strip():
                    pages.append(
                        ParsedPage(
                            page_number=page_num + 1,
                            content=page_text,
                            heading=heading_text if page_num == 0 else None,
                            heading_level=1 if page_num == 0 else None,
                            element_type="NarrativeText",
                            source=file_path.name,
                        )
                    )
                    full_text_parts.append(page_text)

            if not title:
                if pages:
                    title = pages[0].heading or file_path.stem
                else:
                    title = file_path.stem

        finally:
            doc.close()

        full_text = "\n\n".join(full_text_parts)

        logger.debug(
            "NativePDFParser: %s — %d pages, %d sections, %d chars",
            file_path.name, len(pages), len(sections), len(full_text),
        )

        return ParsedDocument(
            title=title,
            content=full_text,
            pages=pages,
            full_text=full_text,
            sections=sections,
            source_path=str(file_path),
            metadata={
                "type": PDFType.NATIVE.value,
                "parser": "NativePDFParser",
                "pages": len(pages),
                "native_pages": len(pages),
                "scanned_pages": 0,
            },
        )
