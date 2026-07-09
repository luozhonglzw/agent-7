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
from pathlib import Path


@dataclass
class ParsedPage:
    """Content extracted from a single page or section.

    Attributes:
        page_number: 1-based page number (None for single-page formats).
        content: Text content of the page.
        heading: Section heading associated with this page (if any).
        heading_level: Heading hierarchy level (1-6).
        element_type: Semantic element type (Title, NarrativeText, Table,
            ListItem, etc.).  Populated by UnstructuredParser; other
            parsers leave it as the default empty string.
        source: Source filename.  Populated by the parser so downstream
            components can trace content back to its origin.
    """

    page_number: int | None = None
    content: str = ""
    heading: str | None = None
    heading_level: int | None = None
    element_type: str = ""
    source: str = ""

    def to_dict(self) -> dict:
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
class ParsedDocument:
    """Unified output from all document parsers.

    Every parser produces this structure so downstream components
    (chunking, embedding, indexing) never need to know the source
    format.

    Attributes:
        title: Document title (from metadata, first heading, or filename).
        pages: Ordered list of parsed pages/sections.
        full_text: Concatenated plain text of the entire document.
        metadata: Format-specific metadata (author, creation date, etc.).
    """

    title: str = ""
    pages: list[ParsedPage] = field(default_factory=list)
    full_text: str = ""
    metadata: dict = field(default_factory=dict)

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


class BaseParser(abc.ABC):
    """Abstract base class for document parsers.

    Subclasses must implement :meth:`parse` and :meth:`supported_extensions`.

    Usage::

        parser = PDFParser()
        if parser.supports(Path("report.pdf")):
            doc = parser.parse(Path("report.pdf"))
    """

    @abc.abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a file and return a ``ParsedDocument``.

        Args:
            file_path: Absolute path to the file to parse.

        Returns:
            Parsed document with extracted text and metadata.

        Raises:
            ParserError: If parsing fails.
        """

    @abc.abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return the file extensions this parser handles.

        Returns:
            List of lowercase extensions including the leading dot,
            e.g. ``[".pdf"]``.
        """

    def supports(self, file_path: Path) -> bool:
        """Check whether this parser can handle the given file.

        Args:
            file_path: Path to check.

        Returns:
            ``True`` if the file extension is in
            :meth:`supported_extensions`.
        """
        return file_path.suffix.lower() in self.supported_extensions()


class ParserError(Exception):
    """Raised when a parser fails to extract content from a file."""

    def __init__(self, detail: str = "", file_path: str = "") -> None:
        self.detail = detail
        self.file_path = file_path
        super().__init__(f"Parser error for '{file_path}': {detail}")
