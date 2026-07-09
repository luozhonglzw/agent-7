"""Source code file parser.

Reads code files and returns a single-page document with the
file's source text.  Useful for code search and Q&A.

Usage::

    from app.core.parsers.code_parser import CodeParser

    parser = CodeParser()
    doc = parser.parse(Path("main.py"))
"""

import logging
from pathlib import Path

from app.core.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParserError

logger = logging.getLogger(__name__)


class CodeParser(BaseParser):
    """Source code parser.

    Treats the entire file as a single page.  Tries UTF-8 with
    strict error handling so binary files are rejected early.
    """

    def supported_extensions(self) -> list[str]:
        """Return supported extensions.

        Returns:
            Common source code file extensions.
        """
        return [
            ".py", ".pyi",
            ".js", ".jsx", ".mjs", ".cjs",
            ".ts", ".tsx",
            ".java", ".kt", ".kts",
            ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".swift",
            ".scala",
            ".sh", ".bash", ".zsh",
            ".sql",
            ".r", ".R",
            ".lua",
            ".pl",
            ".css", ".scss", ".less",
            ".html", ".htm", ".xml",
            ".json", ".yaml", ".yml", ".toml",
        ]

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a source code file.

        Args:
            file_path: Absolute path to the source file.

        Returns:
            Parsed document with a single page.

        Raises:
            ParserError: If the file cannot be read.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ParserError(
                detail="File is not valid UTF-8 text",
                file_path=str(file_path),
            )
        except Exception as exc:
            raise ParserError(
                detail=f"Cannot read file: {exc}",
                file_path=str(file_path),
            ) from exc

        page = ParsedPage(
            page_number=1,
            content=content,
            element_type="NarrativeText",
            source=file_path.name,
        )

        logger.debug(
            "Parsed code %s: %d chars", file_path.name, len(content),
        )

        return ParsedDocument(
            title=file_path.name,
            pages=[page],
            full_text=content,
            metadata={"language": file_path.suffix.lstrip("."), "source": file_path.name},
        )
