"""PDF document parser using PyMuPDF.

Extracts text, headings, and tables from PDF files.

Usage::

    from app.core.parsers.pdf_parser import PDFParser

    parser = PDFParser()
    doc = parser.parse(Path("report.pdf"))
"""

import logging
from pathlib import Path

from app.core.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParserError

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """PDF parser backed by PyMuPDF (fitz).

    Extracts page-level text and attempts heading detection via
    font-size heuristics.
    """

    def supported_extensions(self) -> list[str]:
        """Return supported extensions.

        Returns:
            List containing ``".pdf"``.
        """
        return [".pdf"]

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a PDF file.

        Iterates over pages, extracts text blocks, and groups them
        into :class:`ParsedPage` objects.  The largest font size on
        the first page is used as the document title when no PDF
        metadata title exists.

        Args:
            file_path: Absolute path to the PDF.

        Returns:
            Parsed document.

        Raises:
            ParserError: If PyMuPDF cannot open the file.
        """
        try:
            import fitz  # pymupdf
        except ImportError as exc:
            raise ParserError(
                detail="pymupdf is not installed", file_path=str(file_path)
            ) from exc

        try:
            doc = fitz.open(str(file_path))
        except Exception as exc:
            raise ParserError(
                detail=f"Cannot open PDF: {exc}", file_path=str(file_path)
            ) from exc

        pages: list[ParsedPage] = []
        full_text_parts: list[str] = []
        title = ""
        metadata: dict = {}

        try:
            # Extract PDF metadata
            meta = doc.metadata or {}
            metadata = {
                k: v for k, v in meta.items() if v
            }
            title = metadata.get("title", "") or ""

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

                page_parts: list[str] = []
                heading: str | None = None
                heading_level: int | None = None
                max_font_size = 0.0

                for block in blocks:
                    if block["type"] != 0:  # skip image blocks
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                            font_size = span.get("size", 0)
                            page_parts.append(text)

                            # Track largest font for title/heading detection
                            if font_size > max_font_size:
                                max_font_size = font_size
                                if page_num == 0 and not title:
                                    heading = text
                                    heading_level = 1

                page_text = " ".join(page_parts)
                if page_text.strip():
                    pages.append(
                        ParsedPage(
                            page_number=page_num + 1,
                            content=page_text,
                            heading=heading,
                            heading_level=heading_level,
                        )
                    )
                    full_text_parts.append(page_text)

            # Use first page heading as title fallback
            if not title and pages:
                title = pages[0].heading or file_path.stem

        finally:
            doc.close()

        full_text = "\n\n".join(full_text_parts)

        logger.debug(
            "Parsed PDF %s: %d pages, %d chars",
            file_path.name, len(pages), len(full_text),
        )

        return ParsedDocument(
            title=title,
            pages=pages,
            full_text=full_text,
            metadata=metadata,
        )
