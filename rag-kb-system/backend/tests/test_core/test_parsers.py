"""Document parser unit tests.

Tests for all parser implementations and the factory.
"""

import tempfile
from pathlib import Path

import pytest

from app.core.parsers.base import ParsedDocument, ParsedPage, ParserError
from app.core.parsers.factory import get_parser, parse_file
from app.core.parsers.text_parser import TXTParser
from app.core.parsers.code_parser import CodeParser
from app.core.parsers.markdown_parser import MarkdownParser


class TestParsedDocument:
    """Tests for ParsedDocument dataclass."""

    def test_empty_document(self) -> None:
        """Test empty ParsedDocument defaults."""
        doc = ParsedDocument()
        assert doc.title == ""
        assert doc.pages == []
        assert doc.full_text == ""
        assert doc.metadata == {}
        assert doc.page_count == 0
        assert doc.char_count == 0

    def test_document_with_pages(self) -> None:
        """Test ParsedDocument with pages."""
        pages = [
            ParsedPage(page_number=1, content="Hello"),
            ParsedPage(page_number=2, content="World"),
        ]
        doc = ParsedDocument(
            title="Test",
            pages=pages,
            full_text="Hello\n\nWorld",
        )
        assert doc.page_count == 2
        assert doc.char_count == 11


class TestTXTParser:
    """Tests for TXTParser."""

    def test_supported_extensions(self) -> None:
        """Test supported extensions."""
        parser = TXTParser()
        exts = parser.supported_extensions()
        assert ".txt" in exts
        assert ".log" in exts

    def test_parse_utf8_file(self, tmp_path: Path) -> None:
        """Test parsing a UTF-8 text file."""
        file = tmp_path / "test.txt"
        file.write_text("Hello World\nSecond line", encoding="utf-8")

        parser = TXTParser()
        doc = parser.parse(file)

        assert doc.title == "test"
        assert doc.page_count == 1
        assert "Hello World" in doc.full_text
        assert "Second line" in doc.full_text

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Test parsing an empty file."""
        file = tmp_path / "empty.txt"
        file.write_text("", encoding="utf-8")

        parser = TXTParser()
        doc = parser.parse(file)

        assert doc.page_count == 1
        assert doc.full_text == ""

    def test_parse_gbk_file(self, tmp_path: Path) -> None:
        """Test parsing a GBK-encoded file."""
        file = tmp_path / "chinese.txt"
        file.write_text("你好世界", encoding="gbk")

        parser = TXTParser()
        doc = parser.parse(file)

        assert "你好世界" in doc.full_text


class TestCodeParser:
    """Tests for CodeParser."""

    def test_supported_extensions(self) -> None:
        """Test supported extensions include common languages."""
        parser = CodeParser()
        exts = parser.supported_extensions()
        assert ".py" in exts
        assert ".js" in exts
        assert ".ts" in exts
        assert ".java" in exts
        assert ".cpp" in exts
        assert ".go" in exts
        assert ".rs" in exts

    def test_parse_python_file(self, tmp_path: Path) -> None:
        """Test parsing a Python file."""
        file = tmp_path / "main.py"
        file.write_text('def hello():\n    print("Hello")\n', encoding="utf-8")

        parser = CodeParser()
        doc = parser.parse(file)

        assert doc.title == "main.py"
        assert "def hello():" in doc.full_text
        assert doc.metadata.get("language") == "py"

    def test_parse_json_file(self, tmp_path: Path) -> None:
        """Test parsing a JSON file."""
        file = tmp_path / "config.json"
        file.write_text('{"key": "value"}', encoding="utf-8")

        parser = CodeParser()
        doc = parser.parse(file)

        assert '{"key": "value"}' in doc.full_text


class TestMarkdownParser:
    """Tests for MarkdownParser."""

    def test_supported_extensions(self) -> None:
        """Test supported extensions."""
        parser = MarkdownParser()
        exts = parser.supported_extensions()
        assert ".md" in exts
        assert ".markdown" in exts

    def test_parse_with_headings(self, tmp_path: Path) -> None:
        """Test parsing Markdown with headings."""
        file = tmp_path / "doc.md"
        file.write_text(
            "# Title\n\nIntro text\n\n## Section 1\n\nContent 1\n\n## Section 2\n\nContent 2",
            encoding="utf-8",
        )

        parser = MarkdownParser()
        doc = parser.parse(file)

        assert doc.title == "Title"
        assert doc.page_count >= 2  # At least preamble + sections
        assert any(p.heading == "Section 1" for p in doc.pages)

    def test_parse_with_frontmatter(self, tmp_path: Path) -> None:
        """Test parsing Markdown with YAML frontmatter."""
        file = tmp_path / "fm.md"
        file.write_text(
            '---\ntitle: My Doc\nauthor: Test\n---\n\n# Heading\n\nBody',
            encoding="utf-8",
        )

        parser = MarkdownParser()
        doc = parser.parse(file)

        assert doc.title == "My Doc"
        assert doc.metadata.get("author") == "Test"

    def test_parse_plain_markdown(self, tmp_path: Path) -> None:
        """Test parsing Markdown without headings."""
        file = tmp_path / "plain.md"
        file.write_text("Just some text\nwith multiple lines", encoding="utf-8")

        parser = MarkdownParser()
        doc = parser.parse(file)

        assert doc.title == "plain"
        assert "Just some text" in doc.full_text


class TestParserFactory:
    """Tests for parser factory."""

    def test_get_parser_for_pdf(self) -> None:
        """Test factory returns PDFParser for .pdf."""
        parser = get_parser(Path("test.pdf"))
        assert type(parser).__name__ == "PDFParser"

    def test_get_parser_for_docx(self) -> None:
        """Test factory returns DOCXParser for .docx."""
        parser = get_parser(Path("test.docx"))
        assert type(parser).__name__ == "DOCXParser"

    def test_get_parser_for_md(self) -> None:
        """Test factory returns MarkdownParser for .md."""
        parser = get_parser(Path("test.md"))
        assert type(parser).__name__ == "MarkdownParser"

    def test_get_parser_for_txt(self) -> None:
        """Test factory returns TXTParser for .txt."""
        parser = get_parser(Path("test.txt"))
        assert type(parser).__name__ == "TXTParser"

    def test_get_parser_for_py(self) -> None:
        """Test factory returns CodeParser for .py."""
        parser = get_parser(Path("test.py"))
        assert type(parser).__name__ == "CodeParser"

    def test_get_parser_unsupported(self) -> None:
        """Test factory raises ParserError for unsupported extension."""
        with pytest.raises(ParserError, match="No parser"):
            get_parser(Path("test.xyz"))

    def test_parse_file_txt(self, tmp_path: Path) -> None:
        """Test parse_file convenience function."""
        file = tmp_path / "test.txt"
        file.write_text("Hello", encoding="utf-8")

        doc = parse_file(file)
        assert isinstance(doc, ParsedDocument)
        assert "Hello" in doc.full_text
