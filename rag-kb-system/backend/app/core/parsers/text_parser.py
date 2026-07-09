"""Plain text file parser.

Reads UTF-8 (or GBK fallback) text files and returns a single-page
document.

Usage::

    from app.core.parsers.text_parser import TXTParser

    parser = TXTParser()
    doc = parser.parse(Path("notes.txt"))
"""

import logging
from pathlib import Path

from app.core.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParserError

logger = logging.getLogger(__name__)


class TXTParser(BaseParser):
    """Plain text parser.

    Treats the entire file as a single page.  No heading detection.
    """

    def supported_extensions(self) -> list[str]:
        """Return supported extensions.

        Returns:
            List containing ``".txt"``, ``".log"``, ``".csv"``.
        """
        return [".txt", ".log", ".csv"]

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a plain text file.

        Args:
            file_path: Absolute path to the text file.

        Returns:
            Parsed document with a single page.

        Raises:
            ParserError: If the file cannot be read or decoded.
        """
        content = self._read_file(file_path)

        page = ParsedPage(
            page_number=1,
            content=content,
            element_type="NarrativeText",
            source=file_path.name,
        )

        logger.debug(
            "Parsed TXT %s: %d chars", file_path.name, len(content),
        )

        return ParsedDocument(
            title=file_path.stem,
            pages=[page],
            full_text=content,
            metadata={"source": file_path.name},
        )

    @staticmethod
    def _read_file(file_path: Path) -> str:
        """Read a text file with encoding fallback.

        Tries UTF-8 first, then GBK, then latin-1 as last resort.

        Args:
            file_path: Path to read.

        Returns:
            File content as string.

        Raises:
            ParserError: If all encodings fail.
        """
        for encoding in ("utf-8", "gbk", "latin-1"):
            try:
                return file_path.read_text(encoding=encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as exc:
                raise ParserError(
                    detail=f"Cannot read file: {exc}",
                    file_path=str(file_path),
                ) from exc

        raise ParserError(
            detail="Cannot decode file with any supported encoding",
            file_path=str(file_path),
        )
