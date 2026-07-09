"""Complex layout PDF parser using Docling.

Uses Docling's deep-learning-based layout analysis to handle
multi-column text, complex tables, figures, and mixed content.
This is the most capable parser but also the slowest.

Usage::

    from app.core.parsers.pdf.complex_parser import ComplexPDFParser

    parser = ComplexPDFParser()
    doc = parser.parse(Path("academic_paper.pdf"))
"""

import logging
from pathlib import Path

from app.core.parsers.base import (
    ParsedDocument,
    ParsedPage,
    ParsedSection,
    ParsedTable,
    ParserError,
    PDFType,
)

logger = logging.getLogger(__name__)


class ComplexPDFParser:
    """Deep layout analysis parser for complex PDFs.

    Uses Docling to:
    * Detect and follow reading order across columns
    * Extract tables with cell-level precision
    * Identify figures, captions, headers, and footers
    * Provide bounding boxes for every element
    """

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a complex-layout PDF with Docling.

        Args:
            file_path: Path to the PDF.

        Returns:
            Parsed document with full structural analysis.

        Raises:
            ParserError: If Docling is not installed or parsing fails.
        """
        converter = self._get_converter()

        try:
            result = converter.convert(str(file_path))
        except Exception as exc:
            raise ParserError(
                detail=f"Docling conversion failed: {exc}",
                file_path=str(file_path),
            ) from exc

        return self._build_document(result, file_path)

    @staticmethod
    def _get_converter():
        """Initialize Docling converter.

        Returns:
            Docling DocumentConverter instance.

        Raises:
            ParserError: If Docling is not installed.
        """
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise ParserError(
                detail=(
                    "Docling is not installed. Install with: pip install docling"
                ),
            ) from exc

        return DocumentConverter()

    def _build_document(self, result: object, file_path: Path) -> ParsedDocument:
        """Convert Docling result into a ParsedDocument.

        Args:
            result: Docling conversion result.
            file_path: Source file path.

        Returns:
            Parsed document.
        """
        doc = result.document

        pages: list[ParsedPage] = []
        sections: list[ParsedSection] = []
        tables: list[ParsedTable] = []
        full_text_parts: list[str] = []
        title = ""
        page_texts: dict[int, list[str]] = {}

        # Export to dict for structured access
        doc_dict = doc.export_to_dict()

        # Walk through document elements
        for item in doc_dict.get("body", {}).get("children", []):
            element = self._process_element(item, file_path.name)
            if element is None:
                continue

            sect = element["section"]
            sections.append(sect)

            if sect.page is not None:
                page_texts.setdefault(sect.page, []).append(sect.text)

            if not title and sect.type == "Title":
                title = sect.text[:200]

            # Collect tables
            if "table" in element:
                tables.append(element["table"])

        # Build pages from collected text
        for page_num in sorted(page_texts.keys()):
            text = " ".join(page_texts[page_num])
            if text.strip():
                pages.append(
                    ParsedPage(
                        page_number=page_num,
                        content=text,
                        element_type="NarrativeText",
                        source=file_path.name,
                    )
                )
                full_text_parts.append(text)

        if not title:
            title = file_path.stem

        full_text = "\n\n".join(full_text_parts)

        logger.debug(
            "ComplexPDFParser: %s — %d pages, %d sections, %d tables, %d chars",
            file_path.name, len(pages), len(sections), len(tables), len(full_text),
        )

        return ParsedDocument(
            title=title,
            content=full_text,
            pages=pages,
            full_text=full_text,
            sections=sections,
            tables=tables,
            source_path=str(file_path),
            metadata={
                "type": PDFType.COMPLEX.value,
                "parser": "ComplexPDFParser",
                "pages": len(pages),
                "native_pages": len(pages),
                "scanned_pages": 0,
            },
        )

    def _process_element(
        self, item: dict, source: str
    ) -> dict | None:
        """Process a single Docling document element.

        Args:
            item: Element dict from Docling export.
            source: Source filename.

        Returns:
            Dict with "section" and optionally "table", or None.
        """
        item_type = item.get("type", "")

        # Map Docling types to our section types
        type_map = {
            "title": "Title",
            "heading": "Title",
            "paragraph": "NarrativeText",
            "list_item": "ListItem",
            "caption": "NarrativeText",
            "footnote": "NarrativeText",
            "page_footer": "NarrativeText",
            "page_header": "NarrativeText",
        }

        section_type = type_map.get(item_type, "NarrativeText")
        text = item.get("text", "").strip()

        if not text:
            return None

        # Extract page number
        page_num = item.get("prov", [{}])[0].get("page_no") if item.get("prov") else None

        # Extract bounding box
        bbox = None
        if item.get("prov"):
            prov = item["prov"][0]
            if "bbox" in prov:
                b = prov["bbox"]
                bbox = [b.get("l", 0), b.get("t", 0), b.get("r", 0), b.get("b", 0)]

        # Heading level
        level = 0
        if section_type == "Title":
            level = item.get("level", 1)

        sect = ParsedSection(
            type=section_type,
            level=level,
            text=text,
            page=page_num,
            bbox=bbox,
            confidence=1.0,
        )

        result: dict = {"section": sect}

        # Handle tables
        if item_type == "table":
            table_data = self._extract_table(item)
            if table_data:
                result["table"] = table_data

        return result

    @staticmethod
    def _extract_table(item: dict) -> ParsedTable | None:
        """Extract table data from a Docling table element.

        Args:
            item: Table element dict.

        Returns:
            ParsedTable or None.
        """
        grid = item.get("grid")
        if not grid:
            return None

        rows: list[list[str]] = []
        for row in grid.get("data", {}).get("grid", []):
            cells = [str(cell.get("text", "")) for cell in row]
            rows.append(cells)

        if not rows:
            return None

        page_num = item.get("prov", [{}])[0].get("page_no") if item.get("prov") else None

        # Build markdown representation
        md_lines: list[str] = []
        for i, row in enumerate(rows):
            md_lines.append("| " + " | ".join(row) + " |")
            if i == 0:
                md_lines.append("| " + " | ".join(["---"] * len(row)) + " |")

        return ParsedTable(
            page=page_num,
            rows=rows,
            markdown="\n".join(md_lines),
        )
