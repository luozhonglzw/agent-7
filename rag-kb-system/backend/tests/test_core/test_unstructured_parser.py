"""UnstructuredParser and factory routing tests.

Tests for the high-fidelity Unstructured parser, the unified
metadata format, and the factory's smart PDF routing logic.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.parsers.base import ParsedDocument, ParsedPage, ParserError


class TestParsedPageToDict:
    """Tests for ParsedPage.to_dict() unified metadata format."""

    def test_basic_to_dict(self) -> None:
        """Test to_dict returns expected structure."""
        page = ParsedPage(
            page_number=1,
            content="Hello World",
            element_type="NarrativeText",
            source="test.pdf",
        )
        result = page.to_dict()

        assert result["content"] == "Hello World"
        assert result["metadata"]["page"] == 1
        assert result["metadata"]["type"] == "NarrativeText"
        assert result["metadata"]["source"] == "test.pdf"

    def test_title_element(self) -> None:
        """Test Title element type."""
        page = ParsedPage(
            page_number=1,
            content="Chapter 1",
            element_type="Title",
            source="doc.pdf",
        )
        result = page.to_dict()

        assert result["metadata"]["type"] == "Title"

    def test_table_element(self) -> None:
        """Test Table element type."""
        page = ParsedPage(
            page_number=3,
            content="Col1\tCol2\nA\tB",
            element_type="Table",
            source="report.pdf",
        )
        result = page.to_dict()

        assert result["metadata"]["type"] == "Table"
        assert result["metadata"]["page"] == 3

    def test_empty_element_type_defaults_to_text(self) -> None:
        """Test that empty element_type defaults to 'Text'."""
        page = ParsedPage(
            page_number=1,
            content="Some content",
            source="file.txt",
        )
        result = page.to_dict()

        assert result["metadata"]["type"] == "Text"

    def test_none_page_number(self) -> None:
        """Test to_dict with None page_number."""
        page = ParsedPage(
            content="Content",
            element_type="NarrativeText",
            source="file.txt",
        )
        result = page.to_dict()

        assert result["metadata"]["page"] is None

    def test_backward_compatible_fields(self) -> None:
        """Test that old fields still work alongside new ones."""
        page = ParsedPage(
            page_number=1,
            content="text",
            heading="My Heading",
            heading_level=2,
            element_type="Title",
            source="doc.md",
        )

        # Old fields still accessible
        assert page.heading == "My Heading"
        assert page.heading_level == 2
        # New fields also accessible
        assert page.element_type == "Title"
        assert page.source == "doc.md"
        # to_dict uses new format
        result = page.to_dict()
        assert result["metadata"]["type"] == "Title"


class TestUnstructuredParserImport:
    """Tests for UnstructuredParser import handling."""

    def test_parser_class_exists(self) -> None:
        """Test that UnstructuredParser can be imported when defined."""
        from app.core.parsers.unstructured_parser import UnstructuredParser

        parser = UnstructuredParser()
        assert ".pdf" in parser.supported_extensions()
        assert ".docx" in parser.supported_extensions()

    def test_unsupported_extension_raises(self) -> None:
        """Test that unsupported extensions raise ParserError."""
        from app.core.parsers.unstructured_parser import UnstructuredParser

        parser = UnstructuredParser()
        with pytest.raises(ParserError, match="does not support"):
            parser.parse(Path("file.xyz"))

    def test_parse_pdf_missing_unstructured(self) -> None:
        """Test parse raises helpful error when unstructured not installed."""
        from app.core.parsers.unstructured_parser import UnstructuredParser

        parser = UnstructuredParser()

        with patch(
            "app.core.parsers.unstructured_parser.partition_pdf",
            side_effect=ImportError("No module"),
            create=True,
        ):
            with pytest.raises(ParserError, match="not installed"):
                parser.parse(Path("test.pdf"))


class TestUnstructuredBuildDocument:
    """Tests for _build_document helper."""

    def test_builds_document_from_elements(self) -> None:
        """Test converting Unstructured elements to ParsedDocument."""
        from app.core.parsers.unstructured_parser import UnstructuredParser

        # Mock Unstructured elements
        title_elem = MagicMock()
        title_elem.__str__ = lambda self: "Document Title"
        type(title_elem).__name__ = "Title"
        title_elem.metadata.page_number = 1

        body_elem = MagicMock()
        body_elem.__str__ = lambda self: "Body text paragraph."
        type(body_elem).__name__ = "NarrativeText"
        body_elem.metadata.page_number = 1

        table_elem = MagicMock()
        table_elem.__str__ = lambda self: "Col1\tCol2\nA\tB"
        type(table_elem).__name__ = "Table"
        table_elem.metadata.page_number = 2

        elements = [title_elem, body_elem, table_elem]

        parser = UnstructuredParser()
        doc = parser._build_document(elements, Path("test.pdf"))

        assert doc.title == "Document Title"
        assert doc.page_count == 3
        assert len(doc.full_text) > 0
        assert doc.pages[0].element_type == "Title"
        assert doc.pages[1].element_type == "NarrativeText"
        assert doc.pages[2].element_type == "Table"
        assert doc.pages[0].source == "test.pdf"

    def test_empty_elements(self) -> None:
        """Test with empty element list."""
        from app.core.parsers.unstructured_parser import UnstructuredParser

        parser = UnstructuredParser()
        doc = parser._build_document([], Path("empty.pdf"))

        assert doc.title == "empty"
        assert doc.page_count == 0
        assert doc.full_text == ""


class TestFactoryRouting:
    """Tests for the factory's smart PDF routing."""

    def test_get_parser_for_pdf_returns_pymupdf(self) -> None:
        """Test default PDF parser is PDFParser (PyMuPDF)."""
        from app.core.parsers.factory import get_parser

        parser = get_parser(Path("test.pdf"))
        assert type(parser).__name__ == "PDFParser"

    def test_get_parser_force_unstructured(self) -> None:
        """Test force_unstructured returns UnstructuredParser."""
        from app.core.parsers.factory import get_parser

        with patch(
            "app.core.parsers.factory._get_unstructured_parser"
        ) as mock_get:
            mock_parser = MagicMock()
            mock_get.return_value = mock_parser

            parser = get_parser(Path("test.pdf"), force_unstructured=True)
            assert parser is mock_parser

    def test_get_parser_force_unstructured_not_installed(self) -> None:
        """Test force_unstructured raises when not installed."""
        from app.core.parsers.factory import get_parser

        with patch(
            "app.core.parsers.factory._get_unstructured_parser",
            return_value=None,
        ):
            with pytest.raises(ParserError, match="not installed"):
                get_parser(Path("test.pdf"), force_unstructured=True)

    def test_factory_fallback_on_scanned_pdf(self, tmp_path: Path) -> None:
        """Test factory falls back to Unstructured for text-poor PDFs."""
        from app.core.parsers.factory import parse_file

        # Create a fake PDF file
        pdf_path = tmp_path / "scan.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake content")

        # Mock PyMuPDF parser to return very little text (scanned)
        mock_pymupdf_doc = ParsedDocument(
            title="scan",
            pages=[ParsedPage(page_number=1, content="   ", source="scan.pdf")],
            full_text="   ",
        )

        mock_unstructured_doc = ParsedDocument(
            title="Scanned Document",
            pages=[
                ParsedPage(
                    page_number=1,
                    content="Full OCR text from scanned document",
                    element_type="NarrativeText",
                    source="scan.pdf",
                )
            ],
            full_text="Full OCR text from scanned document",
        )

        with patch(
            "app.core.parsers.factory.PDFParser.parse",
            return_value=mock_pymupdf_doc,
        ), patch(
            "app.core.parsers.factory._get_unstructured_parser"
        ) as mock_get:
            mock_us = MagicMock()
            mock_us.parse.return_value = mock_unstructured_doc
            mock_get.return_value = mock_us

            doc = parse_file(pdf_path)

            # Should have fallen back to Unstructured
            mock_us.parse.assert_called_once()
            assert doc.full_text == "Full OCR text from scanned document"

    def test_factory_keeps_pymupdf_for_text_rich_pdf(self, tmp_path: Path) -> None:
        """Test factory keeps PyMuPDF for text-rich digital PDFs."""
        from app.core.parsers.factory import parse_file

        pdf_path = tmp_path / "digital.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake content")

        # Mock PyMuPDF parser to return rich text
        rich_text = "A" * 5000
        mock_pymupdf_doc = ParsedDocument(
            title="Digital PDF",
            pages=[
                ParsedPage(
                    page_number=1,
                    content=rich_text,
                    source="digital.pdf",
                )
            ],
            full_text=rich_text,
        )

        with patch(
            "app.core.parsers.factory.PDFParser.parse",
            return_value=mock_pymupdf_doc,
        ):
            doc = parse_file(pdf_path)

            # Should NOT have called Unstructured
            assert doc.full_text == rich_text

    def test_parse_file_force_unstructured(self, tmp_path: Path) -> None:
        """Test parse_file with force_unstructured=True."""
        from app.core.parsers.factory import parse_file

        pdf_path = tmp_path / "scan.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        mock_doc = ParsedDocument(title="Test", full_text="OCR result")

        with patch(
            "app.core.parsers.factory._get_unstructured_parser"
        ) as mock_get:
            mock_us = MagicMock()
            mock_us.parse.return_value = mock_doc
            mock_get.return_value = mock_us

            doc = parse_file(pdf_path, force_unstructured=True)

            mock_us.parse.assert_called_once_with(pdf_path)
            assert doc.full_text == "OCR result"
