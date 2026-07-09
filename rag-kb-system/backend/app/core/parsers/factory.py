"""Parser factory with intelligent routing.

Selects the correct parser for a given file extension.  For PDF files
the factory applies a heuristic:

1. Try PyMuPDF (fast, digital-native PDFs).
2. If the extracted text is suspiciously short (scanned / complex
   layout), fall back to ``UnstructuredParser`` (hi_res + OCR).

Other file types always use their dedicated lightweight parser.

Usage::

    from app.core.parsers.factory import parse_file

    # Auto-select (PyMuPDF → Unstructured fallback for PDFs)
    doc = parse_file(Path("report.pdf"))

    # Force Unstructured for a specific file
    doc = parse_file(Path("scan.pdf"), force_unstructured=True)
"""

import logging
from pathlib import Path

from app.core.parsers.base import BaseParser, ParsedDocument, ParserError
from app.core.parsers.code_parser import CodeParser
from app.core.parsers.docx_parser import DOCXParser
from app.core.parsers.markdown_parser import MarkdownParser
from app.core.parsers.pdf_parser import PDFParser
from app.core.parsers.pptx_parser import PPTXParser
from app.core.parsers.text_parser import TXTParser

logger = logging.getLogger(__name__)

# ── Lightweight parsers (always available) ─────────────────────
_PARSERS: list[BaseParser] = [
    PDFParser(),
    DOCXParser(),
    MarkdownParser(),
    PPTXParser(),
    TXTParser(),
    CodeParser(),
]

# Extension → parser lookup cache (built on first call).
_EXT_MAP: dict[str, BaseParser] | None = None

# Minimum average characters-per-page for a "text-rich" PDF.
# Below this threshold we suspect a scanned document and switch
# to UnstructuredParser.
_MIN_CHARS_PER_PAGE = 100


def _get_unstructured_parser() -> BaseParser | None:
    """Try to import and instantiate UnstructuredParser.

    Returns:
        UnstructuredParser instance, or ``None`` if unstructured
        is not installed.
    """
    try:
        from app.core.parsers.unstructured_parser import UnstructuredParser
        return UnstructuredParser()
    except ImportError:
        logger.debug("unstructured library not available — skipping")
        return None


def _build_ext_map() -> dict[str, BaseParser]:
    """Build extension-to-parser mapping.

    Returns:
        Mapping from lowercase extension to parser instance.
    """
    global _EXT_MAP  # noqa: PLW0603
    if _EXT_MAP is not None:
        return _EXT_MAP

    _EXT_MAP = {}
    for parser in _PARSERS:
        for ext in parser.supported_extensions():
            if ext in _EXT_MAP:
                logger.warning(
                    "Extension %s registered by multiple parsers (%s, %s) — "
                    "using first match",
                    ext,
                    type(_EXT_MAP[ext]).__name__,
                    type(parser).__name__,
                )
                continue
            _EXT_MAP[ext] = parser

    logger.debug(
        "Parser registry: %s",
        {k: type(v).__name__ for k, v in _EXT_MAP.items()},
    )
    return _EXT_MAP


def get_parser(
    file_path: Path,
    *,
    force_unstructured: bool = False,
) -> BaseParser:
    """Return the parser for *file_path*.

    For PDF and DOCX files, ``force_unstructured=True`` selects
    ``UnstructuredParser`` directly (useful for known-scanned docs).

    Args:
        file_path: File to find a parser for.
        force_unstructured: If ``True``, return ``UnstructuredParser``
            for PDF/DOCX regardless of content heuristics.

    Returns:
        Matching parser instance.

    Raises:
        ParserError: If no parser supports the extension or
            ``force_unstructured=True`` but unstructured is not
            installed.
    """
    ext = file_path.suffix.lower()

    # ── Explicit override ─────────────────────────────────────
    if force_unstructured and ext in (".pdf", ".docx", ".doc"):
        us = _get_unstructured_parser()
        if us is None:
            raise ParserError(
                detail="force_unstructured=True but unstructured is not installed",
                file_path=str(file_path),
            )
        return us

    # ── Default lookup ────────────────────────────────────────
    ext_map = _build_ext_map()
    parser = ext_map.get(ext)
    if parser is None:
        raise ParserError(
            detail=f"No parser for extension '{ext}'",
            file_path=str(file_path),
        )
    return parser


def parse_file(
    file_path: Path,
    *,
    force_unstructured: bool = False,
) -> ParsedDocument:
    """Parse a file using the appropriate parser.

    For PDFs the factory tries PyMuPDF first.  If the extracted text
    is below the "scanned document" threshold it automatically
    retries with ``UnstructuredParser`` (when installed).

    Args:
        file_path: Absolute path to the file.
        force_unstructured: Bypass heuristics and use
            ``UnstructuredParser`` for PDF/DOCX.

    Returns:
        Parsed document.

    Raises:
        ParserError: If no parser exists or parsing fails.
    """
    ext = file_path.suffix.lower()

    # ── PDF: smart routing ────────────────────────────────────
    if ext == ".pdf" and not force_unstructured:
        return _parse_pdf_with_fallback(file_path)

    # ── DOCX: optional Unstructured override ──────────────────
    if ext in (".docx", ".doc") and not force_unstructured:
        parser = get_parser(file_path)
        logger.info("Parsing %s with %s", file_path.name, type(parser).__name__)
        return parser.parse(file_path)

    # ── Everything else (or forced Unstructured) ──────────────
    parser = get_parser(file_path, force_unstructured=force_unstructured)
    logger.info("Parsing %s with %s", file_path.name, type(parser).__name__)
    return parser.parse(file_path)


def _parse_pdf_with_fallback(file_path: Path) -> ParsedDocument:
    """Parse a PDF with PyMuPDF, falling back to Unstructured.

    Heuristic: if the average characters-per-page from PyMuPDF is
    below ``_MIN_CHARS_PER_PAGE``, the PDF is likely scanned and
    needs OCR.

    Args:
        file_path: Path to the PDF.

    Returns:
        Parsed document.
    """
    pymupdf_parser = PDFParser()

    try:
        doc = pymupdf_parser.parse(file_path)
    except Exception as exc:
        logger.warning(
            "PyMuPDF failed for %s (%s), trying Unstructured",
            file_path.name, exc,
        )
        return _fallback_to_unstructured(file_path)

    # Heuristic check
    if doc.page_count > 0:
        avg_chars = doc.char_count / doc.page_count
        if avg_chars < _MIN_CHARS_PER_PAGE:
            logger.info(
                "PDF %s has only %.0f avg chars/page (< %d) — "
                "switching to UnstructuredParser",
                file_path.name, avg_chars, _MIN_CHARS_PER_PAGE,
            )
            return _fallback_to_unstructured(file_path)

    logger.debug(
        "PDF %s parsed with PyMuPDF: %d pages, %d chars",
        file_path.name, doc.page_count, doc.char_count,
    )
    return doc


def _fallback_to_unstructured(file_path: Path) -> ParsedDocument:
    """Parse with UnstructuredParser, raising if unavailable.

    Args:
        file_path: Path to the file.

    Returns:
        Parsed document.

    Raises:
        ParserError: If unstructured is not installed.
    """
    us = _get_unstructured_parser()
    if us is None:
        raise ParserError(
            detail=(
                "Document appears to be scanned but unstructured "
                "library is not installed.  Install with: "
                "pip install 'unstructured[pdf]'"
            ),
            file_path=str(file_path),
        )
    return us.parse(file_path)
