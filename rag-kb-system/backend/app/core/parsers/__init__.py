"""Document parsers for various file formats.

Provides parsers for extracting text content from uploaded documents.
All parsers return a unified :class:`ParsedDocument` structure.

Parsers:
    PDFParser:      PDF document parser (PyMuPDF)
    DOCXParser:     Word document parser (python-docx)
    MarkdownParser: Markdown file parser
    TXTParser:      Plain text file parser
    PPTXParser:     PowerPoint parser (python-pptx)
    CodeParser:     Source code file parser

Factory:
    parse_file:     Auto-select parser and parse a file
    get_parser:     Get the parser for a given file extension

Usage::

    from app.core.parsers import parse_file, ParsedDocument

    doc = parse_file(Path("report.pdf"))
    print(doc.title, doc.page_count, len(doc.full_text))
"""

from app.core.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParserError
from app.core.parsers.factory import get_parser, parse_file

__all__ = [
    "BaseParser",
    "ParsedDocument",
    "ParsedPage",
    "ParserError",
    "get_parser",
    "parse_file",
]
