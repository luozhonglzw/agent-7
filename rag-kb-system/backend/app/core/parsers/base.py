"""Base parser and unified document structure.

All format-specific parsers inherit from ``BaseParser`` and return
a ``ParsedDocument`` instance, giving the rest of the pipeline a
single data shape to work with regardless of source format.

Usage::

    from app.core.parsers.base import ParsedDocument, BaseParser

    class MyParser(BaseParser):
        def parse(self, file_path: Path) -> ParsedDocument:
            ...
"""

import abc
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# PDF Classification Types
# ═══════════════════════════════════════════════════════════════


class PDFType(str, Enum):
    """PDF document type classification.

    The classifier examines each page to determine the overall type.
    """

    NATIVE = "native"      # 100% digital text (PyMuPDF direct extraction)
    SCANNED = "scanned"    # 100% image-based (requires OCR)
    HYBRID = "hybrid"      # Mix of digital and scanned pages
    COMPLEX = "complex"    # Complex layout (multi-column, tables, figures)


@dataclass
class PageClassification:
    """Per-page classification result.

    Attributes:
        page_number: 1-based page number.
        text_blocks: Number of text blocks detected.
        text_ratio: Ratio of text area to page area (0.0–1.0).
        image_count: Number of images on the page.
        page_type: Classified page type (native/scanned).
        confidence: Classification confidence (0.0–1.0).
    """

    page_number: int
    text_blocks: int = 0
    text_ratio: float = 0.0
    image_count: int = 0
    page_type: str = "native"
    confidence: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Parsed Page / Section / Table
# ═══════════════════════════════════════════════════════════════


@dataclass
class ParsedPage:
    """Content extracted from a single page or section.

    Attributes:
        page_number: 1-based page number (None for single-page formats).
        content: Text content of the page.
        heading: Section heading associated with this page (if any).
        heading_level: Heading hierarchy level (1-6).
        element_type: Semantic element type (Title, NarrativeText, Table,
            ListItem, etc.).
        source: Source filename.
    """

    page_number: int | None = None
    content: str = ""
    heading: str | None = None
    heading_level: int | None = None
    element_type: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the unified metadata format.

        Returns::

            {
                "content": "<text>",
                "metadata": {"page": 1, "type": "Title", "source": "file.pdf"}
            }
        """
        return {
            "content": self.content,
            "metadata": {
                "page": self.page_number,
                "type": self.element_type or "Text",
                "source": self.source,
            },
        }


@dataclass
class ParsedSection:
    """A semantic section extracted from the document.

    Carries structural information (heading level, bounding box)
    so that downstream components can reconstruct the document
    outline and provide precise citations.

    Attributes:
        type: Element type (Title, NarrativeText, Table, ListItem, …).
        level: Heading level (1-6, 0 for non-heading elements).
        text: Section text content.
        page: 1-based page number where the section starts.
        bbox: Bounding box ``[x0, y0, x1, y1]`` in PDF points (if known).
        confidence: Extraction confidence (0.0–1.0, 1.0 for digital text).
    """

    type: str = "NarrativeText"
    level: int = 0
    text: str = ""
    page: int | None = None
    bbox: list[float] | None = None
    confidence: float = 1.0


@dataclass
class ParsedTable:
    """A table extracted from the document.

    Attributes:
        page: 1-based page number.
        rows: Table data as list of rows (each row is a list of strings).
        bbox: Bounding box ``[x0, y0, x1, y1]`` in PDF points.
        html: HTML representation of the table (if available).
        markdown: Markdown representation of the table.
    """

    page: int | None = None
    rows: list[list[str]] = field(default_factory=list)
    bbox: list[float] | None = None
    html: str = ""
    markdown: str = ""

    @property
    def row_count(self) -> int:
        """Number of rows."""
        return len(self.rows)

    @property
    def col_count(self) -> int:
        """Number of columns (width of the widest row)."""
        return max((len(r) for r in self.rows), default=0)


# ═══════════════════════════════════════════════════════════════
# Unified Parsed Document
# ═══════════════════════════════════════════════════════════════


@dataclass
class ParsedDocument:
    """Unified output from all document parsers.

    Every parser produces this structure so downstream components
    (chunking, embedding, indexing) never need to know the source
    format.

    Attributes:
        title: Document title.
        content: Full plain text (alias for full_text).
        pages: Ordered list of parsed pages/sections.
        full_text: Concatenated plain text of the entire document.
        sections: Semantic sections with type/bbox/confidence.
        tables: Extracted tables with cell data.
        source_path: Absolute path to the source file.
        metadata: Format-specific metadata (author, creation date, etc.).
    """

    title: str = ""
    content: str = ""
    pages: list[ParsedPage] = field(default_factory=list)
    full_text: str = ""
    sections: list[ParsedSection] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    source_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Sync content and full_text if only one is set."""
        if self.full_text and not self.content:
            self.content = self.full_text
        elif self.content and not self.full_text:
            self.full_text = self.content

    @property
    def page_count(self) -> int:
        """Number of parsed pages.

        Returns:
            Page count (0 if no pages).
        """
        return len(self.pages)

    @property
    def char_count(self) -> int:
        """Total character count.

        Returns:
            Length of full_text.
        """
        return len(self.full_text)

    @property
    def pdf_type(self) -> str | None:
        """PDF classification type (if set in metadata).

        Returns:
            PDF type string or None.
        """
        return self.metadata.get("type")
