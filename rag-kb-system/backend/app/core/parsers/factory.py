"""Parser factory.

Selects the correct parser for a given file extension and provides
a single ``parse_file`` convenience function.

Usage::

    from app.core.parsers.factory import parse_file

    doc = parse_file(Path("report.pdf"))
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

# Registry of all available parsers, instantiated once.
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

    logger.debug("Parser registry: %s", {k: type(v).__name__ for k, v in _EXT_MAP.items()})
    return _EXT_MAP


def get_parser(file_path: Path) -> BaseParser:
    """Return the parser for *file_path*'s extension.

    Args:
        file_path: File to find a parser for.

    Returns:
        Matching parser instance.

    Raises:
        ParserError: If no parser supports the extension.
    """
    ext_map = _build_ext_map()
    ext = file_path.suffix.lower()
    parser = ext_map.get(ext)
    if parser is None:
        raise ParserError(
            detail=f"No parser for extension '{ext}'",
            file_path=str(file_path),
        )
    return parser


def parse_file(file_path: Path) -> ParsedDocument:
    """Parse a file using the appropriate parser.

    Convenience wrapper around :func:`get_parser` + ``parser.parse``.

    Args:
        file_path: Absolute path to the file.

    Returns:
        Parsed document.

    Raises:
        ParserError: If no parser exists or parsing fails.
    """
    parser = get_parser(file_path)
    logger.info("Parsing %s with %s", file_path.name, type(parser).__name__)
    return parser.parse(file_path)
