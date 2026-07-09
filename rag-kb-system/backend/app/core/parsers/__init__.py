"""Document parsers for various file formats.

Provides parsers for extracting text content from uploaded documents.
All parsers return a unified :class:`ParsedDocument` structure.

PDF Classification Pipeline:
    PDFClassifier:      Classify PDFs into native/scanned/hybrid/complex
    ParserFactory:      Auto-classify + dispatch to specialized parser
    NativePDFParser:    Digital text extraction (PyMuPDF)
    ScannedPDFParser:   OCR via PaddleOCR (pdf2image + PaddleOCR)
    HybridPDFParser:    Per-page routing (native ↔ scanned)
    ComplexPDFParser:   Deep layout analysis (Docling)

Legacy Parsers:
    PDFParser:          Simple PDF parser (PyMuPDF)
    DOCXParser:         Word document parser (python-docx)
    MarkdownParser:     Markdown file parser
    TXTParser:          Plain text file parser
    PPTXParser:         PowerPoint parser (python-pptx)
    CodeParser:         Source code file parser
    UnstructuredParser: High-fidelity parser via Unstructured (optional)

Factory:
    parse_file:     Auto-select parser and parse a file
    get_parser:     Get the parser for a given file extension

Usage::

    from app.core.parsers import (
        parse_file, ParsedDocument, PDFType,
        ParserFactory, PDFClassifier,
    )

    # Legacy: simple file parsing
    doc = parse_file(Path("report.pdf"))

    # New: PDF classification pipeline
    doc = ParserFactory.parse_file(Path("report.pdf"))
    print(doc.metadata["type"])   # "native" / "scanned" / "hybrid" / "complex"
    print(doc.metadata["parser"]) # "NativePDFParser" / ...

    # Explicit classification
    classifier = PDFClassifier()
    pdf_type, pages = classifier.classify(Path("scan.pdf"))
    doc = ParserFactory.parse_file(Path("scan.pdf"), pdf_type=pdf_type)
"""

from app.core.parsers.base import (
    BaseParser,
    ParsedDocument,
    ParsedPage,
    ParsedSection,
    ParsedTable,
    ParserError,
    PDFType,
    PageClassification,
)
from app.core.parsers.factory import get_parser, parse_file
from app.core.parsers.pdf_classifier import PDFClassifier
from app.core.parsers.parser_factory import ParserFactory

__all__ = [
    # Base types
    "BaseParser",
    "ParsedDocument",
    "ParsedPage",
    "ParsedSection",
    "ParsedTable",
    "ParserError",
    "PDFType",
    "PageClassification",
    # Legacy factory
    "get_parser",
    "parse_file",
    # New pipeline
    "PDFClassifier",
    "ParserFactory",
]
