"""PDF classification pipeline tests.

Tests for PDFClassifier, the four specialized parsers, and
the ParserFactory routing logic.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.parsers.base import (
    PageClassification,
    ParsedDocument,
    ParsedSection,
    ParsedTable,
    PDFType,
)
from app.core.parsers.pdf_classifier import PDFClassifier


# ═══════════════════════════════════════════════════════════════
# ParsedDocument extended fields
# ═══════════════════════════════════════════════════════════════


class TestParsedDocumentExtended:
    """Tests for the new ParsedDocument fields."""

    def test_sections_field(self) -> None:
        """Test sections field is populated."""
        sections = [
            ParsedSection(type="Title", level=1, text="Chapter 1", page=1),
            ParsedSection(type="NarrativeText", text="Body text", page=1),
        ]
        doc = ParsedDocument(title="Test", sections=sections)
        assert len(doc.sections) == 2
        assert doc.sections[0].type == "Title"

    def test_tables_field(self) -> None:
        """Test tables field is populated."""
        tables = [
            ParsedTable(
                page=1,
                rows=[["A", "B"], ["1", "2"]],
                markdown="| A | B |\n| --- | --- |\n| 1 | 2 |",
            )
        ]
        doc = ParsedDocument(title="Test", tables=tables)
        assert len(doc.tables) == 1
        assert doc.tables[0].row_count == 2
        assert doc.tables[0].col_count == 2

    def test_source_path_field(self) -> None:
        """Test source_path field."""
        doc = ParsedDocument(title="Test", source_path="/tmp/test.pdf")
        assert doc.source_path == "/tmp/test.pdf"

    def test_content_aliases_full_text(self) -> None:
        """Test content and full_text are synced."""
        doc = ParsedDocument(content="Hello World")
        assert doc.full_text == "Hello World"
        assert doc.content == "Hello World"

    def test_pdf_type_from_metadata(self) -> None:
        """Test pdf_type property reads from metadata."""
        doc = ParsedDocument(
            title="Test",
            metadata={"type": "scanned"},
        )
        assert doc.pdf_type == "scanned"

    def test_pdf_type_none_when_unset(self) -> None:
        """Test pdf_type returns None when not in metadata."""
        doc = ParsedDocument(title="Test")
        assert doc.pdf_type is None

    def test_backward_compatible_pages(self) -> None:
        """Test that pages field still works."""
        from app.core.parsers.base import ParsedPage

        pages = [ParsedPage(page_number=1, content="text")]
        doc = ParsedDocument(title="Test", pages=pages, full_text="text")
        assert doc.page_count == 1
        assert doc.char_count == 4


# ═══════════════════════════════════════════════════════════════
# PDF Classifier
# ═══════════════════════════════════════════════════════════════


class TestPDFClassifier:
    """Tests for PDFClassifier."""

    def test_page_classification_dataclass(self) -> None:
        """Test PageClassification defaults."""
        pc = PageClassification(page_number=1)
        assert pc.page_number == 1
        assert pc.text_blocks == 0
        assert pc.text_ratio == 0.0
        assert pc.image_count == 0
        assert pc.page_type == "native"
        assert pc.confidence == 0.0

    def test_pdf_type_enum_values(self) -> None:
        """Test PDFType enum has all four values."""
        assert PDFType.NATIVE.value == "native"
        assert PDFType.SCANNED.value == "scanned"
        assert PDFType.HYBRID.value == "hybrid"
        assert PDFType.COMPLEX.value == "complex"

    def test_classifier_classify_mocked(self, tmp_path: Path) -> None:
        """Test classifier with mocked PyMuPDF."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=3)
        mock_page = MagicMock()
        mock_page.rect = MagicMock(width=612, height=792)
        mock_page.get_text.return_value = {
            "blocks": [
                {"type": 0, "bbox": (10, 10, 500, 50)},
                {"type": 0, "bbox": (10, 60, 500, 100)},
            ]
        }
        mock_page.get_images.return_value = []
        mock_doc.load_page.return_value = mock_page

        with patch("fitz.open", return_value=mock_doc):
            classifier = PDFClassifier()
            pdf_type, pages = classifier.classify(pdf_path)

        assert pdf_type == PDFType.NATIVE
        assert len(pages) == 3
        assert all(p.page_type == "native" for p in pages)

    def test_classifier_detects_scanned(self, tmp_path: Path) -> None:
        """Test classifier detects scanned pages."""
        pdf_path = tmp_path / "scan.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)
        mock_page = MagicMock()
        mock_page.rect = MagicMock(width=612, height=792)
        mock_page.get_text.return_value = {"blocks": []}
        mock_page.get_images.return_value = [("img1",), ("img2",)]
        mock_doc.load_page.return_value = mock_page

        with patch("fitz.open", return_value=mock_doc):
            classifier = PDFClassifier()
            pdf_type, pages = classifier.classify(pdf_path)

        assert pdf_type == PDFType.SCANNED
        assert all(p.page_type == "scanned" for p in pages)

    def test_classifier_detects_hybrid(self, tmp_path: Path) -> None:
        """Test classifier detects mixed native/scanned pages."""
        pdf_path = tmp_path / "hybrid.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        call_count = 0

        def make_page(page_type: str):
            page = MagicMock()
            page.rect = MagicMock(width=612, height=792)
            if page_type == "native":
                page.get_text.return_value = {
                    "blocks": [
                        {"type": 0, "bbox": (10, 10, 500, 50)},
                        {"type": 0, "bbox": (10, 60, 500, 100)},
                        {"type": 0, "bbox": (10, 110, 500, 150)},
                        {"type": 0, "bbox": (10, 160, 500, 200)},
                    ]
                }
                page.get_images.return_value = []
            else:
                page.get_text.return_value = {"blocks": []}
                page.get_images.return_value = [("img",)]
            return page

        native_page = make_page("native")
        scanned_page = make_page("scanned")

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)
        mock_doc.load_page.side_effect = [native_page, scanned_page]

        with patch("fitz.open", return_value=mock_doc):
            classifier = PDFClassifier()
            pdf_type, pages = classifier.classify(pdf_path)

        assert pdf_type == PDFType.HYBRID


# ═══════════════════════════════════════════════════════════════
# Parser Factory
# ═══════════════════════════════════════════════════════════════


class TestParserFactory:
    """Tests for ParserFactory."""

    def test_get_parser_native(self) -> None:
        """Test get_parser returns NativePDFParser for NATIVE."""
        from app.core.parsers.parser_factory import ParserFactory

        parser = ParserFactory.get_parser(PDFType.NATIVE)
        assert type(parser).__name__ == "NativePDFParser"

    def test_get_parser_scanned(self) -> None:
        """Test get_parser returns ScannedPDFParser for SCANNED."""
        from app.core.parsers.parser_factory import ParserFactory

        parser = ParserFactory.get_parser(PDFType.SCANNED)
        assert type(parser).__name__ == "ScannedPDFParser"

    def test_get_parser_hybrid(self) -> None:
        """Test get_parser returns HybridPDFParser for HYBRID."""
        from app.core.parsers.parser_factory import ParserFactory

        parser = ParserFactory.get_parser(PDFType.HYBRID)
        assert type(parser).__name__ == "HybridPDFParser"

    def test_get_parser_complex(self) -> None:
        """Test get_parser returns ComplexPDFParser for COMPLEX."""
        from app.core.parsers.parser_factory import ParserFactory

        parser = ParserFactory.get_parser(PDFType.COMPLEX)
        assert type(parser).__name__ == "ComplexPDFParser"

    def test_parse_file_not_found(self) -> None:
        """Test parse_file raises on missing file."""
        from app.core.parsers.parser_factory import ParserFactory

        with pytest.raises(Exception, match="not found|File not found"):
            ParserFactory.parse_file(Path("/nonexistent/file.pdf"))

    def test_parse_file_with_explicit_type(self, tmp_path: Path) -> None:
        """Test parse_file with explicit pdf_type skips classification."""
        from app.core.parsers.parser_factory import ParserFactory

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        mock_doc = ParsedDocument(
            title="Test",
            content="parsed text",
            metadata={"type": "native", "parser": "NativePDFParser"},
        )

        with patch.object(
            ParserFactory, "_parse_with_fallback", return_value=mock_doc
        ) as mock_parse:
            doc = ParserFactory.parse_file(pdf_path, pdf_type=PDFType.NATIVE)

        mock_parse.assert_called_once_with(pdf_path, PDFType.NATIVE)
        assert doc.content == "parsed text"

    def test_fallback_chain_complex(self) -> None:
        """Test fallback chain for COMPLEX type."""
        from app.core.parsers.parser_factory import ParserFactory

        chain = ParserFactory._get_fallback_chain(PDFType.COMPLEX)
        assert chain == [PDFType.HYBRID, PDFType.NATIVE]

    def test_fallback_chain_scanned(self) -> None:
        """Test fallback chain for SCANNED type."""
        from app.core.parsers.parser_factory import ParserFactory

        chain = ParserFactory._get_fallback_chain(PDFType.SCANNED)
        assert chain == [PDFType.HYBRID]


# ═══════════════════════════════════════════════════════════════
# Section / Table dataclasses
# ═══════════════════════════════════════════════════════════════


class TestParsedSection:
    """Tests for ParsedSection dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        sect = ParsedSection()
        assert sect.type == "NarrativeText"
        assert sect.level == 0
        assert sect.text == ""
        assert sect.page is None
        assert sect.bbox is None
        assert sect.confidence == 1.0

    def test_title_section(self) -> None:
        """Test a Title section."""
        sect = ParsedSection(
            type="Title",
            level=1,
            text="Chapter 1: Introduction",
            page=1,
            bbox=[72, 100, 540, 130],
            confidence=0.95,
        )
        assert sect.type == "Title"
        assert sect.level == 1
        assert sect.bbox[2] == 540


class TestParsedTable:
    """Tests for ParsedTable dataclass."""

    def test_row_col_count(self) -> None:
        """Test row_count and col_count."""
        table = ParsedTable(
            rows=[["A", "B", "C"], ["1", "2", "3"]],
        )
        assert table.row_count == 2
        assert table.col_count == 3

    def test_empty_table(self) -> None:
        """Test empty table."""
        table = ParsedTable()
        assert table.row_count == 0
        assert table.col_count == 0

    def test_markdown_field(self) -> None:
        """Test markdown representation."""
        table = ParsedTable(
            rows=[["Name", "Age"], ["Alice", "30"]],
            markdown="| Name | Age |\n| --- | --- |\n| Alice | 30 |",
        )
        assert "| Name |" in table.markdown
