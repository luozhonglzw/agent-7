"""Markdown file parser.

Extracts frontmatter metadata and splits content by headings.

Usage::

    from app.core.parsers.markdown_parser import MarkdownParser

    parser = MarkdownParser()
    doc = parser.parse(Path("readme.md"))
"""

import logging
import re
from pathlib import Path

from app.core.parsers.base import BaseParser, ParsedDocument, ParsedPage, ParserError

logger = logging.getLogger(__name__)

# Matches Markdown headings: # through ######
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# Matches YAML frontmatter delimited by ---
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class MarkdownParser(BaseParser):
    """Markdown parser with frontmatter support.

    Splits the document on headings into pages, preserving heading
    hierarchy.  YAML frontmatter (if present) is parsed into the
    metadata dict.
    """

    def supported_extensions(self) -> list[str]:
        """Return supported extensions.

        Returns:
            List containing ``".md"``, ``".markdown"``, ``".mdown"``.
        """
        return [".md", ".markdown", ".mdown"]

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a Markdown file.

        Args:
            file_path: Absolute path to the Markdown file.

        Returns:
            Parsed document.

        Raises:
            ParserError: If the file cannot be read.
        """
        try:
            raw = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                raw = file_path.read_text(encoding="gbk")
            except Exception as exc:
                raise ParserError(
                    detail=f"Cannot decode file: {exc}",
                    file_path=str(file_path),
                ) from exc
        except Exception as exc:
            raise ParserError(
                detail=f"Cannot read file: {exc}",
                file_path=str(file_path),
            ) from exc

        title = ""
        metadata: dict = {}

        # ── Extract frontmatter ───────────────────────────────
        fm_match = _FRONTMATTER_RE.match(raw)
        if fm_match:
            raw_body = raw[fm_match.end():]
            metadata = self._parse_frontmatter(fm_match.group(1))
            title = metadata.get("title", "")
        else:
            raw_body = raw

        # ── Split by headings into pages ──────────────────────
        pages: list[ParsedPage] = []
        full_text_parts: list[str] = []

        splits = re.split(r"^(#{1,6}\s+.+)$", raw_body, flags=re.MULTILINE)

        # splits[0] = content before first heading (or all content if no headings)
        source_name = file_path.name

        preamble = splits[0].strip()
        if preamble:
            pages.append(ParsedPage(
                page_number=1,
                content=preamble,
                element_type="NarrativeText",
                source=source_name,
            ))
            full_text_parts.append(preamble)

        # Remaining pairs: (heading_line, content_after_heading)
        page_counter = len(pages) + 1
        for i in range(1, len(splits), 2):
            heading_line = splits[i].strip()
            body = splits[i + 1].strip() if i + 1 < len(splits) else ""

            hm = _HEADING_RE.match(heading_line)
            if hm:
                level = len(hm.group(1))
                heading_text = hm.group(2).strip()
            else:
                level = 1
                heading_text = heading_line.lstrip("#").strip()

            if not title:
                title = heading_text

            content = f"{heading_line}\n\n{body}" if body else heading_line
            pages.append(
                ParsedPage(
                    page_number=page_counter,
                    content=content,
                    heading=heading_text,
                    heading_level=level,
                    element_type="Title",
                    source=source_name,
                )
            )
            full_text_parts.append(content)
            page_counter += 1

        if not title:
            title = file_path.stem

        full_text = "\n\n".join(full_text_parts)

        logger.debug(
            "Parsed Markdown %s: %d pages, %d chars",
            file_path.name, len(pages), len(full_text),
        )

        metadata["source"] = source_name
        return ParsedDocument(
            title=title,
            pages=pages,
            full_text=full_text,
            metadata=metadata,
        )

    @staticmethod
    def _parse_frontmatter(text: str) -> dict:
        """Parse simple YAML frontmatter into a dict.

        Handles ``key: value`` lines only (no nested structures).

        Args:
            text: Raw frontmatter content between ``---`` delimiters.

        Returns:
            Parsed key-value pairs.
        """
        result: dict = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                result[key.strip()] = value.strip().strip("\"'")
        return result
